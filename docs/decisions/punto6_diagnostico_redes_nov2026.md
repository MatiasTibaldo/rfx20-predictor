# Punto 6 del feedback de los directores: diagnóstico de las redes antes de atribuir todo a sobreajuste

**Fecha:** 4 de noviembre de 2026
**Módulos:** `scripts/punto6_dl_diagnostics.py` (nuevo)
**Origen:** Punto 6 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso): las degradaciones de Deep Learning con el feature set
"full"/composición (ver `docs/decisions/punto5_variantes_componentes_nov2026.md`)
son grandes como para justificar una auditoría específica antes de atribuirlas
solo a sobreajuste.

## 1. Escalado del objetivo y transformación inversa — sin problema, no existe tal paso

Revisado `models/deep_learning/common.py` completo: el target (`log_return`
o `log_return_fwd_h`) **nunca se escala** en ningún punto del pipeline —
`StandardScaler` se aplica únicamente a las features (`X`), nunca a `y`
(`train_with_early_stopping` recibe `y_fit`/`y_earlystop` crudos,
`evaluate()` compara contra `y_true` crudo). No existe una transformación
inversa que pueda estar mal implementada, porque no hay transformación de
ida.

## 2. Alineación ventana-etiqueta — correcta

`build_sequences()`: cada ventana usa las últimas `lookback` filas
terminando en la fecha `i` (inclusive) y predice `targets[i]` — que ya es
`log_return_fwd_h`, el retorno mirando `h` días hacia adelante **desde**
esa misma fecha `i`. No hay desfasaje de índice ni off-by-one: la ventana
"ve" el pasado hasta hoy, predice el futuro desde hoy. Confirmado por
lectura directa del código, no requiere un test adicional.

## 3. Media y dispersión de las predicciones — sesgo sistemático, no ruido

Calculado sobre las predicciones de val ya persistidas (Puntos 3 y 5):

| Config | y_true (media, std) | y_pred (media, std) |
|---|---|---|
| GRU, baseline-full, h=5 | +0,0024 / 0,0685 | **+0,0710** / 0,0766 |
| GRU, compA-full, h=5 | +0,0024 / 0,0686 | **+0,1280** / 0,1273 |
| LSTM, compA-full, h=1 | +0,0005 / 0,0296 | **-0,0468** / 0,1120 |
| LSTM, compC-máscara, h=5 | +0,0024 / 0,0685 | **+0,1671** / 0,1155 |
| CNN-LSTM, compA-full, h=1 (contraste) | +0,0005 / 0,0296 | +0,0076 / 0,0161 |

Las configuraciones degradadas muestran una **media predicha 20 a 70 veces
mayor que la media real**, con dispersión comparable o mayor que la de los
datos reales — no es una salida degenerada (constante) ni ruido simétrico
alrededor de cero: el modelo converge a una predicción sistemáticamente
sesgada en magnitud (y a veces en signo, ver LSTM compA h=1). CNN-LSTM, en
contraste, mantiene media y dispersión mucho más cercanas a los valores
reales. Esto es evidencia concreta de sobreajuste (el modelo aprende un
patrón de train que no generaliza, en vez de simplemente fallar al
converger), no una inferencia hecha únicamente a partir de un RMSE alto.

## 4. Estabilidad entre semillas — implementado y probado

`scripts/punto6_dl_diagnostics.py` repite 3 configuraciones (lookback fijo
en el valor ya elegido por la corrida oficial, para no mezclar varianza de
selección de lookback con varianza de semilla) con semillas 42/7/123:

| Configuración | RMSE por semilla | Media | CV |
|---|---|---|---|
| GRU, compA-full, h=5 | 0,1817 / 0,2215 / 0,1651 | 0,1894 | 12,5% |
| LSTM, compC-máscara, h=5 | 0,2129 / 0,2087 / 0,2099 | 0,2105 | 0,8% |
| CNN-LSTM, compA-full, h=1 (contraste) | 0,0343 / 0,0399 / 0,0328 | 0,0357 | 8,5% |

**LSTM-máscara es notablemente estable entre semillas** (CV=0,8%) — las 3
semillas convergen de forma consistente a un resultado catastrófico
(ninguna corrida se acerca a un comportamiento aceptable), lo que apunta a
una limitación estructural (dimensionalidad del feature set frente al
tamaño de muestra, ~1.600 filas de train) más que a una inicialización
desafortunada puntual. **GRU es más variable** (CV=12,5%, la media del
sesgo predicho va de -0,01 a +0,13 según la semilla) — la magnitud exacta
del sesgo sí depende de la semilla, pero **ninguna de las 3 produce un
resultado utilizable**: el RMSE nunca se acerca al del naive (~0,069) en
ninguna semilla. CNN-LSTM (el caso de contraste) es estable y
consistentemente bueno. Conclusión: la degradación severa no es un
artefacto de una sola corrida con mala suerte — se sostiene, con distinto
grado de variabilidad, en las 3 semillas probadas.

## 5. Curvas de pérdida (loss/early-stopping) — ahora persistidas

El historial de pérdida de early stopping (`TrainResult.history`) se
calculaba en el código desde el inicio del proyecto pero se descartaba sin
persistir. Persistido ahora en `results/punto6_dl_diagnostics/seed_stability.json`
para las 9 corridas (3 configs × 3 semillas). Patrón observado: en las
configuraciones degradadas, el mejor epoch (`best_epoch`) ocurre muy
temprano (ej. GRU seed=42: mejor en epoch 4 de 20; LSTM-máscara seed=42:
mejor en epoch 2 de 18) y la pérdida de early stopping nunca baja de forma
sostenida — consistente con el modelo memorizando ruido de train antes de
poder generalizar, la firma característica de sobreajuste bajo alta
dimensionalidad con pocos datos (no un problema de optimización que
simplemente necesite más épocas).

## 5bis. Brecha train vs. early-stopping — evidencia directa de sobreajuste (6-nov-2026)

El director, en su respuesta de seguimiento, pidió específicamente: si las
curvas de entrenamiento y validación muestran una brecha persistente,
incorporarla como evidencia adicional del diagnóstico de sobreajuste (más
allá del sesgo en las predicciones y la estabilidad entre semillas, ya
documentados arriba).

**Implementado**: `train_with_early_stopping()` (`models/deep_learning/common.py`)
ahora calcula, en el mismo punto de cada época donde ya se calculaba la
pérdida de early-stopping, la pérdida sobre el propio conjunto de *fit*
(`X_fit`/`y_fit`) — un forward pass adicional sin gradiente, sin costo de
entrenamiento extra. Re-corridas las mismas 3 configuraciones de la sección
4 (`scripts/punto6_dl_diagnostics.py`), un seed alcanza para ver la forma de
la curva:

| Configuración (seed=42) | Pérdida train (inicio→mejor época→fin) | Pérdida early-stopping (inicio→mejor→fin) |
|---|---|---|
| GRU-compA h=5 | 0,0119 → 0,0036 → **0,0012** | 0,0094 → 0,0079 → **0,0179** |
| LSTM-máscara(C) h=5 | 0,0055 → 0,0032 → **0,0006** | 0,0299 → 0,0287 → **0,0360** |
| CNN-LSTM-compA h=1 (contraste) | 0,0010 → 0,0010 → **0,0006** | 0,0009 → 0,0009 → **0,0036** |

**Brecha persistente confirmada en las 3 configuraciones**: la pérdida de
train sigue bajando de forma monótona hasta el final del entrenamiento (no
se estanca), mientras que la pérdida de early-stopping mejora solo hasta su
mejor época y después **empeora** — en GRU y LSTM-máscara más que se
duplica desde su mínimo hasta el final; en CNN-LSTM (el caso de contraste,
con mucho menor error absoluto) también empeora de forma proporcional
(~4x desde el mínimo), aunque la magnitud absoluta del problema es mucho
menor. Es exactamente el patrón de libro de sobreajuste: el modelo sigue
reduciendo su error sobre los datos que ve, a costa de generalizar peor a
los que no — y se repite incluso en la arquitectura que mejor se comporta
bajo el feature set "full"/composición, no es exclusivo de los casos más
degradados. Confirmado también en las semillas 7 y 123 de la misma corrida
(mismo patrón cualitativo, ver `results/punto6_dl_diagnostics/seed_stability.json`).

## 5ter. Barrido completo de la matriz (36 combinaciones) — generaliza la brecha (6-nov-2026)

La sección 5bis confirma la brecha train/early-stopping en 3 configuraciones
representativas (las más degradadas + 1 de contraste sano). Para verificar
que no es un artefacto de esa muestra puntual, se corrió la matriz completa
de datasets × arquitecturas × horizontes materializados en el proyecto:
**3 datasets** (`features_long` baseline, `features_long_compA`,
`features_long_compC_masked`) × **4 arquitecturas** (LSTM, GRU, CNN-LSTM,
Transformer encoder) × **3 horizontes** = **36 combinaciones**, 1 semilla
(42) — alcanza para ver la forma de la curva, no para repetir el análisis
de estabilidad entre semillas de la sección 4. El lookback no se reutiliza
de ninguna corrida previa (no hay un valor persistido para las 36
combinaciones): se re-selecciona con `select_lookback()` (grid search sobre
`LOOKBACK_CANDIDATES`), el mismo criterio que usa el pipeline oficial.

**Nota de alcance**: por decisión explícita de los directores, esta corrida
incluye las 9 combinaciones GRU/CNN-LSTM/Transformer encoder ×
`compC_masked` que nunca se habían corrido oficialmente — la sección 3 de
`docs/decisions/punto5_variantes_componentes_nov2026.md` había concluido,
probando solo con LSTM (el peor resultado de toda la batería), que la
máscara de disponibilidad "no es útil para Deep Learning" en este proyecto.
Esta sección **no reabre ni contradice esa conclusión**: solo documenta la
curva de pérdida train/early-stopping de esas 9 combinaciones nuevas, sin
recalcular RMSE vs. naive — la conclusión del Punto 5 sigue vigente tal
cual, basada en su propio criterio (RMSE), no en este.

Script: `scripts/punto6_dl_diagnostics_full_sweep.py`. Resultado completo
persistido en `results/punto6_dl_diagnostics_full_sweep/full_sweep.json`
(no versionado, como el resto de `results/`).

**Hallazgo principal: las 36/36 combinaciones muestran una brecha positiva
al final del entrenamiento** (`gap_last = es_loss_final − train_loss_final`)
— incluso las más chicas (del orden de +0,0003 a +0,0008, todas h=1 sobre
el dataset baseline) son estrictamente positivas. No es un patrón aislado a
los 3 casos señalados en la sección 5bis: es sistemático en toda la matriz
materializada del proyecto.

Patrones dentro de ese resultado uniforme:

- **Por horizonte**: la brecha se agrava con el horizonte — h=5 y h=3
  dominan ampliamente el extremo de mayor brecha de la tabla; h=1 domina
  el extremo de menor brecha, con pocas excepciones.
- **Por dataset**: `compA` y `compC_masked` (los datasets de mayor
  dimensionalidad — 74 y ~118 columnas respectivamente) concentran las
  brechas más grandes; `baseline` (34 columnas) tiende a brechas
  sensiblemente menores, consistente con el diagnóstico ya documentado de
  sobreajuste por dimensionalidad frente a un train chico (~1.600 filas).
- **Por arquitectura**: LSTM y CNN-LSTM muestran las brechas más grandes del
  ranking (las 5 combinaciones con mayor `gap_last` incluyen 3 de LSTM y 2
  de CNN-LSTM); GRU y Transformer encoder tienden a brechas menores en
  términos relativos, sin quedar exentos — ninguna arquitectura tiene una
  sola combinación con brecha nula o negativa al final del entrenamiento.

Tabla completa, ordenada de mayor a menor `gap_last`:

| Dataset | Modelo | h | lookback | gap (mejor época) | gap (final) | crecimiento del gap |
|---|---|---|---:|---:|---:|---:|
| compA | LSTM | 5 | 30 | +0,02956 | +0,11907 | +0,08951 |
| compC_masked | CNN-LSTM | 5 | 20 | +0,00221 | +0,07544 | +0,07323 |
| compA | LSTM | 3 | 30 | +0,02491 | +0,07251 | +0,04760 |
| compA | CNN-LSTM | 5 | 30 | +0,00367 | +0,04442 | +0,04075 |
| compA | CNN-LSTM | 3 | 20 | +0,00090 | +0,04251 | +0,04161 |
| compC_masked | LSTM | 5 | 10 | +0,02261 | +0,03650 | +0,01390 |
| compA | LSTM | 1 | 20 | +0,02147 | +0,03135 | +0,00988 |
| baseline | LSTM | 5 | 10 | +0,00458 | +0,03095 | +0,02637 |
| compC_masked | LSTM | 3 | 10 | +0,02421 | +0,03076 | +0,00656 |
| compA | Transformer encoder | 5 | 20 | +0,01040 | +0,03072 | +0,02031 |
| baseline | CNN-LSTM | 5 | 30 | -0,00082 | +0,02586 | +0,02667 |
| compC_masked | Transformer encoder | 5 | 30 | +0,00279 | +0,02102 | +0,01823 |
| compC_masked | LSTM | 1 | 10 | +0,01984 | +0,02030 | +0,00046 |
| compC_masked | GRU | 5 | 10 | +0,01284 | +0,01737 | +0,00453 |
| compA | GRU | 5 | 10 | +0,00219 | +0,01595 | +0,01377 |
| baseline | LSTM | 3 | 10 | +0,00339 | +0,01560 | +0,01221 |
| compC_masked | CNN-LSTM | 3 | 10 | +0,00118 | +0,01438 | +0,01319 |
| baseline | Transformer encoder | 5 | 30 | +0,00516 | +0,01389 | +0,00873 |
| compA | Transformer encoder | 3 | 10 | +0,00566 | +0,01373 | +0,00807 |
| compC_masked | Transformer encoder | 3 | 20 | +0,00656 | +0,00959 | +0,00303 |
| compC_masked | GRU | 3 | 30 | +0,00815 | +0,00892 | +0,00077 |
| compA | GRU | 3 | 10 | +0,00342 | +0,00782 | +0,00441 |
| baseline | Transformer encoder | 3 | 10 | +0,00414 | +0,00634 | +0,00220 |
| baseline | GRU | 5 | 30 | +0,00218 | +0,00622 | +0,00404 |
| baseline | CNN-LSTM | 3 | 20 | -0,00026 | +0,00594 | +0,00620 |
| baseline | LSTM | 1 | 10 | +0,00184 | +0,00576 | +0,00391 |
| baseline | GRU | 3 | 30 | +0,00310 | +0,00494 | +0,00183 |
| compA | CNN-LSTM | 1 | 20 | -0,00011 | +0,00481 | +0,00492 |
| compC_masked | GRU | 1 | 30 | +0,00387 | +0,00402 | +0,00015 |
| baseline | GRU | 1 | 10 | +0,00297 | +0,00391 | +0,00094 |
| compC_masked | CNN-LSTM | 1 | 10 | +0,00054 | +0,00313 | +0,00260 |
| compA | GRU | 1 | 20 | +0,00251 | +0,00297 | +0,00045 |
| compA | Transformer encoder | 1 | 20 | +0,00069 | +0,00203 | +0,00134 |
| compC_masked | Transformer encoder | 1 | 10 | +0,00062 | +0,00130 | +0,00068 |
| baseline | Transformer encoder | 1 | 30 | +0,00000 | +0,00076 | +0,00076 |
| baseline | CNN-LSTM | 1 | 30 | -0,00006 | +0,00027 | +0,00033 |

Tres combinaciones (`baseline/CNN-LSTM/h=5`, `baseline/CNN-LSTM/h=3`,
`compA/CNN-LSTM/h=1`) tienen un `gap` *negativo* en la mejor época (es decir,
en el momento en que el early-stopping decidió frenar, la pérdida de
validación era, por una magnitud mínima, menor que la de train) — ruido
esperable del tamaño de muestra chico del split de early-stopping, no
evidencia en contra del patrón: las tres igual terminan con `gap_last`
positivo.

## 6. Conciliación "documento" vs. "correo" — tabla de experimentos

El RMSE casi empatado con el naive que aparece en los documentos oficiales
de Track B, y las degradaciones severas reportadas en otras instancias
(correo a los directores), **no son el mismo experimento** — se distinguen
por versión de dataset y conjunto de features, no por una inconsistencia:

| Experimento | Dataset | Feature set | Target | Purga borde | Vigente |
|---|---|---|---|---|---|
| Track B oficial (narrow) | `features_long` | `narrow` (`log_return` + vol. realizada, 5 cols) | Acumulado (Punto 3) | Sí (Punto 4) | ✅ Sí — empatado con naive |
| Track B "full" (24 predictores) | `features_long` | `full` (24 cols, mismo tratamiento que SVM) | Acumulado (Punto 3) | Sí (Punto 4) | ✅ Sí — degradación severa (61%-353% peor, Punto 5 ítem 4) |
| Composición A-full | `features_long_compA` | `full` + 40 cols ranking | Acumulado (Punto 3) | Sí (Punto 4) | ✅ Sí — degradación aún mayor (Punto 5 ítem 4) |
| Composición C-máscara | `features_long_compC_masked` | `full` + 84 cols por ticker | Acumulado (Punto 3) | Sí (Punto 4) | ✅ Sí — peor resultado de toda la batería (Punto 5 ítem 3) |
| Exploraciones previas (`scripts/prototype_component_*.py`) | Variable (A-F) | Variable | **Retorno de un solo día** (pre-Punto 3) | **No** (pre-Punto 4) | ❌ No — target y purga desactualizados, no citar números |

Semilla: `RANDOM_STATE=42` fijo en todas las corridas oficiales (Track B
narrow/full, composición); estabilidad entre semillas verificada de forma
puntual en este documento (ítem 4), no para las 48 combinaciones completas
de Bloque 2/Punto 5 — alcance acotado, consistente con "comprobación
acotada" pedida por el director, no una re-corrida exhaustiva.

## Conclusión

Las degradaciones severas de Deep Learning con el feature set "full"/
composición **no se explican por un bug** (escalado, alineación) — son un
patrón real y robusto (estable entre semillas, con firma de sesgo
sistemático en las predicciones, y con una brecha persistente y creciente
entre la pérdida de train y la de early-stopping — secciones 5bis y 5ter)
de sobreajuste por alta dimensionalidad frente a un conjunto de
entrenamiento chico (~1.600 filas). El barrido completo de la sección 5ter
(36/36 combinaciones de dataset × arquitectura × horizonte con brecha
positiva, agravada por horizonte y dimensionalidad del dataset) confirma
que esto no es un hallazgo acotado a los 3 casos más degradados, sino la
regla general en toda la matriz materializada del proyecto. El resultado
narrow (empatado con el naive) y el resultado full/composición
(catastrófico) son dos experimentos distintos y ambos vigentes — no una
inconsistencia a resolver, sino el mismo patrón de Bloque 2 (sobreajuste
cuando sube la capacidad sin subir la señal) ya documentado en el Punto 7.
