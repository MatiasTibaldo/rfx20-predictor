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
sistemático en las predicciones y de sobreajuste temprano en las curvas de
pérdida) de sobreajuste por alta dimensionalidad frente a un conjunto de
entrenamiento chico (~1.600 filas). El resultado narrow (empatado con el
naive) y el resultado full/composición (catastrófico) son dos experimentos
distintos y ambos vigentes — no una inconsistencia a resolver, sino el
mismo patrón de Bloque 2 (sobreajuste cuando sube la capacidad sin subir la
señal) ya documentado en el Punto 7.
