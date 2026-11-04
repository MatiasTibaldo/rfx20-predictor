# Punto 7 del feedback de los directores: separar conclusiones de retorno, dirección y volatilidad

**Fecha:** 4 de noviembre de 2026
**Módulos:** `scripts/punto7_hitrate.py` (nuevo), `docs/tesis/proyecto_final_tibaldo.md`
(sección 5.4). `docs/tesis/draf_proyecto_final_google_docs.md` no tiene todavía
el Capítulo 5 (llega hasta la metodología, ~884 líneas) — nada que corregir ahí
por ahora; cuando se extienda a ese capítulo debe partir ya de la versión
corregida de `proyecto_final_tibaldo.md`. `docs/avance_trabajo_final.md`
(sección 4.6, "Versión 3" — el documento de avance real enviado a los
directores) tenía la misma síntesis con los mismos problemas; corregido en el
mismo pase (agregado también ahí el hit-rate).
**Origen:** Punto 7 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso).

## El problema señalado

La sección 5.4 ("Síntesis comparativa") del Capítulo 5 afirmaba, en efecto,
que el proyecto había encontrado "ausencia de señal direccional explotable"
y citaba la hipótesis de **mercados eficientes en su forma débil** como
lectura consistente con el resultado. El director objeta tres cosas
puntuales:

1. Un RMSE similar al naive **no demuestra** ausencia de capacidad para
   anticipar el signo del retorno — esa es una dimensión distinta, que
   necesita su propia métrica y referencia (no se medía en el proyecto).
2. Los 10 métodos comparten el mismo dataset, el mismo pipeline de
   features y el mismo protocolo de validación — que todos coincidan **no
   permite descartar una limitación común** (del dato o del protocolo), solo
   porque sean algorítmicamente distintos.
3. **Error conceptual de terminología**: la eficiencia débil es
   específicamente sobre la información contenida en precios y volúmenes
   pasados. El proyecto usa variables macroeconómicas públicas (riesgo país,
   tasas, dólares, futuros) en varios modelos — eso corresponde a un test
   más cercano a la **forma semifuerte** de la hipótesis de eficiencia, no a
   la débil.

## 1. Métrica de dirección — hit-rate, implementado

No existía ninguna métrica de acierto de signo en el proyecto hasta este
punto — toda la evidencia de "ausencia de señal" se apoyaba exclusivamente
en RMSE/MAE, que miden magnitud del error, no si el signo pronosticado
coincide con el real. Implementado en `scripts/punto7_hitrate.py`: para cada
uno de los 9 modelos de dirección (ARIMA, SVM, RF, XGBoost, LightGBM, LSTM,
GRU, CNN-LSTM, TFT-lite) y cada horizonte, usando las predicciones de val ya
persistidas de la re-corrida del Punto 3 (target acumulado, purga de
borde):

- `hit%` = porcentaje de días donde `sign(y_pred) == sign(y_true)`.
- Referencia: no 50% a secas, sino también `%pos_real` (proporción real de
  días con retorno positivo en val) — la referencia correcta si la serie
  tiene drift distinto de cero.
- Test binomial de dos colas contra H0: hit-rate = 50%, por cada
  combinación (modelo, horizonte).

**Resultado — tabla completa (n=294 en los 27 casos):**

| Modelo | h=1 | h=3 | h=5 |
|---|---:|---:|---:|
| ARIMA | 49,32% (p=0,86) | 50,68% (p=0,86) | 52,38% (p=0,45) |
| SVM | 48,98% (p=0,77) | 47,28% (p=0,38) | 47,28% (p=0,38) |
| RF | 54,08% (p=0,18) | 50,00% (p=1,00) | 52,04% (p=0,52) |
| XGBoost | 53,40% (p=0,27) | 55,44% (p=0,07) | 46,26% (p=0,22) |
| LightGBM | 54,42% (p=0,14) | 51,70% (p=0,60) | 51,36% (p=0,68) |
| LSTM | 52,72% (p=0,38) | 51,36% (p=0,68) | 47,96% (p=0,52) |
| GRU | 52,04% (p=0,52) | 46,26% (p=0,22) | 47,28% (p=0,38) |
| CNN-LSTM | 49,32% (p=0,86) | 46,60% (p=0,27) | 46,60% (p=0,27) |
| TFT-lite | 48,64% (p=0,68) | 47,62% (p=0,45) | 51,36% (p=0,68) |

**0 de 27 combinaciones (modelo, horizonte) tienen p < 0,05.** El p-valor
más bajo es XGBoost h=3 (p=0,07), que tampoco cruza el umbral convencional —
con 27 pruebas y sin corrección por comparaciones múltiples, ni siquiera ese
caso sería evidencia sólida (a ese nivel se esperarían ~1-2 falsos positivos
por azar; no apareció ninguno).

**Esto responde directamente la objeción del director**: ya no se infiere la
ausencia de capacidad direccional a partir de un RMSE parecido al naive —
se midió con la métrica correcta (hit-rate + test de hipótesis) y el
resultado es consistente con lo que ya sugería el RMSE, pero ahora con
evidencia propia de esa dimensión.

## 2. Corrección de la sección 5.4 del Capítulo 5

Aplicado directamente en `docs/tesis/proyecto_final_tibaldo.md` (agrega la
subsección nueva 5.4.1 "Dimensión de dirección: hit-rate" con la Tabla 5.8, y
reescribe 5.4.2, antes "tres observaciones"):

- **Formulación de la conclusión** reemplazada por la propuesta del
  director: *"no se encontró una mejora consistente frente al pronóstico de
  retorno cero, bajo los datos, modelos, horizontes y protocolo
  evaluados"* — explícitamente acotada a lo evaluado, sin afirmar que el
  índice no es predecible ni que no existe señal en los datos en términos
  absolutos.
- **La observación 1** ("la consistencia entre métodos... descarta que se
  trate de una mala elección de arquitectura") se reformuló para reconocer
  que los 10 métodos comparten dataset, pipeline de features y protocolo de
  validación — la coincidencia entre ellos es evidencia de que el problema
  (si lo hay) no es específico de un algoritmo puntual, pero no permite
  descartar una limitación común del dato o del protocolo compartido.
- **La observación 3** corregida de "mercados eficientes en su forma
  débil" a **forma semifuerte** — con la aclaración de que varios modelos
  del proyecto usan información pública más amplia que precios/volúmenes
  pasados (macro, futuros), así que la lectura de eficiencia, si se hace,
  corresponde a ese nivel, no al débil.
- Se agrega explícitamente la sección de hit-rate (tabla de arriba) como
  evidencia propia de la dimensión de dirección, distinta del RMSE.
- Se agrega una aclaración sobre la dimensión de volatilidad (GARCH): la
  ausencia de autocorrelación lineal en el retorno (ARIMA) no dice nada
  sobre la volatilidad condicional — son preguntas distintas, y el proyecto
  ya las trata por separado (Tabla 5.7 mantiene a GARCH en su propia fila,
  bajo "volatilidad", nunca mezclado con los 9 modelos de dirección).

## 3. Limpieza relacionada: `track_a_b_sintesis_direccion_volatilidad.md`

Encontrado al cerrar este punto: el documento de síntesis de Bloque 2 tenía,
en su sección final ("Qué significa para lo que sigue"), la afirmación "el
modelo ganador del proyecto, con la evidencia actual, es GARCH" — texto que
**no** estaba marcado como registro histórico (a diferencia de la sección
"Evidencia: volatilidad condicional", que el propio documento preserva sin
editar a propósito desde la actualización de sep-2026) y contradecía
directamente el banner superior del mismo documento. Corregido: agregada una
"Actualización 2 (4 nov 2026)" con las cifras vigentes de GARCH tras el
Punto 3 (pierde en RMSE y QLIKE en los 3 horizontes, no solo "casi empata"),
reescrita la sección final para no declarar ningún modelo ganador, y
corregida la misma cita a "eficiencia débil" → "eficiencia semifuerte" que
en la tesis.

## Pendiente

- El Capítulo 6 (Conclusión) sigue sin escribirse — cuando se redacte, debe
  heredar la formulación acotada de este punto, no la original.
- No se identificó una causa concreta de "limitación común" más allá de lo
  ya documentado (tamaño de muestra chico, ~1600 filas de train) — queda
  como una posibilidad reconocida en el texto, no una hipótesis
  investigada a fondo en esta ronda.
