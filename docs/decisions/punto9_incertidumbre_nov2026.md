# Punto 9 del feedback de los directores: medida de incertidumbre para diferencias pequeñas

**Fecha:** 4 de noviembre de 2026
**Módulos:** `scripts/punto9_bootstrap_ci.py` (nuevo)
**Origen:** Punto 9 del feedback de los directores de tesis (Fernanda Mendez /
Rodrigo Del Rosso).

## 1. Intervalos de confianza por block bootstrap — implementado

Para las 27 combinaciones (9 modelos de dirección × 3 horizontes), calculado
sobre las predicciones de val ya persistidas (Punto 3): RMSE y MAE absolutos,
N, % vs. naive, y un **intervalo de confianza 95% por bootstrap de bloques
móviles** (no i.i.d.) para esa diferencia porcentual.

**Por qué bloques y no bootstrap i.i.d.**: los errores de pronóstico a h días
se solapan entre fechas consecutivas (el target de hoy y el de mañana
comparten h-1 retornos diarios), lo que induce autocorrelación tipo MA(h-1)
incluso si el modelo no tiene memoria — exactamente la preocupación que
señala el director ("dependencia temporal y superposición de horizontes"). Un
bootstrap i.i.d. subestimaría el error estándar al romper esa dependencia.
Longitud de bloque fija en 10 jornadas para los 3 horizontes (simplicidad,
sin optimizar un parámetro adicional sin justificación propia), B=2000
remuestreos.

**Resultado — tabla completa:**

| Modelo | h | RMSE | MAE | % vs. naive | IC 95% | Excluye 0 |
|---|---|---:|---:|---:|---|---|
| ARIMA | 1 | 0,02954 | 0,02085 | -0,06% | [-0,82, +0,83] | No |
| ARIMA | 3 | 0,05245 | 0,03745 | +0,06% | [-0,48, +0,81] | No |
| ARIMA | 5 | 0,06848 | 0,04868 | -0,12% | [-0,48, +0,47] | No |
| RF | 1 | 0,02952 | 0,02084 | -0,12% | [-1,61, +1,15] | No |
| SVM | 1 | 0,02969 | 0,02107 | +0,47% | [-0,78, +1,88] | No |
| XGBoost | 5 | 0,07256 | 0,05169 | +5,84% | [+0,03, +12,11] | **Sí** |
| CNN-LSTM | 1 | 0,03019 | 0,02167 | +2,14% | [+0,31, +4,58] | **Sí** |
| Transformer encoder | 1 | 0,03029 | 0,02164 | +2,50% | [+0,36, +4,99] | **Sí** |
| Transformer encoder | 3 | 0,05565 | 0,04027 | +6,15% | [+0,92, +11,58] | **Sí** |

*(Tabla completa de las 27 filas en `results/punto9_bootstrap/bootstrap_ci_summary.parquet`
y en el output de `scripts/punto9_bootstrap_ci.py`.)*

**Hallazgo central: 0 de 27 combinaciones muestran una mejora significativa
sobre el naive — las pequeñas "mejoras" de ARIMA y RF (<0,4%, exactamente lo
que señala el director) tienen intervalos que incluyen el 0, compatibles con
variabilidad muestral pura.** En cambio, **4 de 27 combinaciones sí son
significativamente peores que el naive** (XGBoost h=5, CNN-LSTM h=1,
Transformer encoder h=1 y h=3) — el único efecto detectable en toda la
batería va en la dirección negativa, nunca en la positiva. Esto fortalece,
con la medida de incertidumbre que pedía el director, la conclusión de
"ninguna mejora consistente": no es solo que no se vea una ventaja — cuando
sí se detecta una diferencia significativa, es contra el modelo, no a favor.

## 2. No sobre-interpretar la mejor celda aislada

Se evaluaron las 27 combinaciones juntas, no una elegida después de ver los
resultados — evita exactamente el problema que señala el director. Nota de
comparaciones múltiples: con 27 pruebas a α=0,05, sería esperable encontrar
~1-2 falsos positivos por azar si la verdadera diferencia fuera cero en
todos los casos; no se encontró ninguno del lado de la mejora (0/27), lo cual
es, si acaso, más consistente con "no hay mejora" que con un resultado
dudoso por multiplicidad de pruebas.

## 3. RMSE/MAE absolutos, N, apertura temporal

Agregados en la misma tabla: RMSE y MAE absolutos (no solo el % relativo) y
N=294 en los 27 casos. Apertura temporal: RMSE sobre la primera vs. segunda
mitad cronológica de val (ver parquet completo) — varios modelos (RF,
XGBoost, LightGBM, GRU en h=3/h=5) muestran una diferencia notable entre
mitades (ej. XGBoost h=5: 0,0643 primera mitad vs. 0,0800 segunda mitad),
indicando que el error no es homogéneo a lo largo de val — consistente con
que la segunda mitad del período de validación atraviesa un tramo de mayor
volatilidad, no con que el resultado dependa de un puñado aislado de
jornadas extremas.

## 4. Evaluación económica acotada — alcance definido, no ejecutada en esta ronda

El director condiciona este ítem explícitamente ("si mantenemos el objetivo
de soporte a decisiones") y lo describe como una evaluación "acotada" sobre
un instrumento efectivamente operable (futuros del RFX20, no el índice de
contado), con costos, ejecución posterior a la señal y posiciones
superpuestas en horizontes de varios días.

**Decisión de alcance**: no se ejecuta en esta ronda. Razón: el Punto 9
(ítems 1-3) y el Punto 7 (hit-rate) ya establecen, con medidas de
incertidumbre propias, que no hay una señal direccional distinguible de cero
en ninguno de los 9 modelos evaluados. Backtestear el costo de operar una
señal que no está estadísticamente distinguible del azar tiene valor
informativo bajo — el resultado esperable es que cualquier costo de
transacción no nulo empeore un punto de partida que ya no tiene ventaja
antes de costos. Este ítem queda documentado como trabajo futuro
bien definido, a retomar **solo si** en una iteración posterior aparece un
modelo con mejora significativa y estable que justifique el esfuerzo de
construir el simulador (datos de futuros ya disponibles en
`data/raw/v1/rfx20_futures.parquet`, pendiente: modelo de costos de
transacción, mapeo señal→ejecución con lag, y tratamiento de posiciones
superpuestas en horizontes >1 día).

## Pendiente

- Si se decide perseguir el ítem 4 en el futuro, diseñarlo como su propio
  punto de trabajo, no como un agregado menor — tiene su propia
  complejidad metodológica (ver razones arriba).
