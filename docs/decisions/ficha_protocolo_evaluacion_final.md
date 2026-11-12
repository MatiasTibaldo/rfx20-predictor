# Ficha de protocolo — evaluación final sobre el conjunto de test reservado

**Fecha:** 6 de noviembre de 2026
**Estado:** borrador para revisión de los directores (Fernanda Mendez /
Rodrigo Del Rosso) — **no se corrió todavía nada sobre el conjunto de test**,
en línea con lo pedido en su mail de seguimiento del 6-nov-2026.

## 1. Conjunto de test

| | |
|---|---|
| Rango de fechas | 2026-04-20 → 2026-08-25 |
| Origen | Datos genuinamente nuevos, traídos vía WebSocket de MatbaRofex con posterioridad al cierre del resto del historial (`docs/decisions/rfx20_ws_backfill.md`) — 100% out-of-sample, nunca usado en ninguna decisión de desarrollo (selección de modelo, hiperparámetros, feature engineering) hasta la fecha |
| N calendario | 86 fechas |
| N efectivo por horizonte (retorno/dirección) | h=1: 85 · h=3: 83 · h=5: 81 (se achica por el target *forward*: los últimos h días de la ventana no tienen retorno acumulado realizado todavía dentro del propio conjunto de test) |

El conjunto de test es válido como out-of-sample aunque sea histórico porque
no intervino en ninguna decisión de desarrollo — es la condición que importa,
no la cronología en sí. No se modificó ninguna decisión de modelado después
de reservarlo.

## 2. Modelos y configuraciones

Los 10 modelos oficiales de Bloque 2, ya evaluados y documentados sobre
validación con el target corregido (Punto 3 del feedback) y el protocolo de
purga vigente (Punto 4):

| Familia | Modelos | Feature set |
|---|---|---|
| Estadística | ARIMA/SARIMA, GARCH | Univariados (solo `log_return` del índice) |
| ML clásico | SVM, Random Forest, XGBoost, LightGBM | Completo (24 predictores, gaps estructurales con nulos reales para árboles, excluidos para SVM) |
| Deep Learning | LSTM, GRU, CNN-LSTM, Transformer encoder | Acotado (`log_return` + volatilidad realizada, 5 columnas) |

No se vuelve a buscar hiperparámetros ni arquitectura sobre test — se usan
exactamente los ya seleccionados sobre train/val (orden ARIMA (0,0,1); orden
GARCH(1,1) t-Student; hiperparámetros de los 4 modelos de ML elegidos por
`RandomizedSearchCV` sobre train; *lookback* de cada red elegido por
*early stopping*, nunca sobre val).

## 3. Política de actualización por familia durante el período de test

**ARIMA y GARCH** continúan el mismo walk-forward diario que ya corre sobre
val: orden/distribución fijos desde la selección original sobre train,
coeficientes reestimados cada día con ventana de historia expansiva (ahora
incluyendo val completo y el tramo de test ya transcurrido). Es una
extensión directa del protocolo existente, no un cambio de diseño.
*Pendiente de implementación*: `walk_forward_evaluate` (`arima.py`) y
`walk_forward_evaluate_variance` (`garch.py`) hoy tienen el split "val"
hardcodeado — hay que generalizarlas para aceptar "test" antes de poder
correr esto.

**SVM, Random Forest, XGBoost, LightGBM, LSTM, GRU, CNN-LSTM, Transformer
encoder** — **propuesta a confirmar en la reunión**: reentrenar cada uno una
única vez, con los hiperparámetros/arquitectura ya seleccionados, ahora sobre
train+val combinado (consistente con el criterio ya documentado del proyecto
de que "el modelo final se reentrena con el dataset completo antes de usarse
en producción" — el split es una herramienta de selección, no una exclusión
permanente), y evaluarlos una sola vez sobre test, sin ningún ajuste
adicional. Alternativa más conservadora, si prefieren no incorporar val al
entrenamiento final: evaluar directamente el modelo ya entrenado sobre train
(el mismo que hoy se reporta sobre val) contra test, sin reentrenar. Ambas
opciones son metodológicamente defendibles; la diferencia es si se usa toda
la información disponible antes de test (opción propuesta) o se mantiene el
modelo exactamente como está documentado hoy (alternativa). Pedimos que lo
definan en la reunión.

## 4. Benchmarks por dimensión

| Dimensión | Benchmark(s) |
|---|---|
| Retorno | Naive de retorno cero (igual que en validación) |
| Dirección | 50% (azar) **y** "mayoría de train" — predecir siempre el signo más frecuente del retorno acumulado en train, por horizonte (el balance no es 50/50: 55,8%/58,0%/59,5% de días positivos en train para h=1/3/5 — agregado al pedido explícito de los directores, ver `docs/decisions/punto7_separar_conclusiones_nov2026.md` sección 2) |
| Volatilidad | Naive de varianza constante (varianza incondicional de train) **y** EWMA (λ=0,94) — GARCH ya le gana a EWMA en validación, pero el naive de varianza constante sigue siendo el de mejor desempeño de los tres (`docs/decisions/garch_volatility_track_a.md`) |

## 5. Métricas

- **Retorno**: RMSE y MAE absolutos + variación % vs. naive, N efectivo por
  horizonte (sección 1).
- **Dirección**: hit-rate (% de aciertos de signo) + test binomial contra
  ambos benchmarks (50% y mayoría de train).
- **Volatilidad**: RMSE y QLIKE del pronóstico de varianza vs. el proxy de
  varianza realizada (retorno acumulado al cuadrado).
- **Incertidumbre**: intervalo de confianza 95% por bootstrap de bloques
  móviles (longitud 10, igual criterio que en validación) para cada
  comparación — **cada intervalo es individual/marginal**, no una región de
  confianza conjunta sobre el conjunto completo de comparaciones (aclaración
  pedida explícitamente por el director, ver
  `docs/decisions/punto9_incertidumbre_nov2026.md`).

## 6. Disponibilidad de predictores en el período de test

Confirmado explícitamente, no asumido: de los 24 predictores del feature set
completo, 2 tienen gaps reales en el tramo de test (N=86):

| Columna | Nulos / N | Tratamiento |
|---|---|---|
| `implied_rate_front` | 2/86 | Gap estructural real (sin contrato *front-month* con dato ese día) |
| `implied_rate_next` | 28/86 | Gap estructural real (sin contrato *next* disponible esos días) |
| `term_spread_futures` | 30/86 | Depende de `implied_rate_next` — mismo gap |

Mismo patrón de gap estructural ya documentado desde Track A
(`docs/decisions/ml_feature_engineering_track_a.md`): los modelos de árbol
(RF/XGBoost/LightGBM) reciben estas columnas con sus nulos reales, sin
imputar; SVM y los 4 modelos de Deep Learning las excluyen de su feature
set. No es un error de datos, no bloquea la evaluación — pero se deja
explícito, como pide el director, en vez de asumir "disponible" sin
chequear.

**Verificado contra la API en vivo (6-nov-2026)**: se re-consultó
`https://apicem.matbarofex.com.ar/api/v2/closing-prices` (mismo endpoint
documentado en `docs/decisions/futures_implied_rate.md`) para las 28 fechas
con `implied_rate_next` nulo — la API sigue devolviendo un único contrato
cotizando esos días, confirmando que es un **gap real de mercado**, no una
limitación de cobertura de la ingesta: no hay forma de completarlo con datos
reales porque el segundo contrato simplemente no cotizó esos días.

**Hallazgo adicional, ya corregido**: la misma re-consulta detectó que
`data/raw/v1/rfx20_futures.parquet` no se había vuelto a descargar desde el
21-ago-2026. Como `features/macro.py::build_macro_features` alinea con
`join_asof(strategy="backward")`, las dos últimas fechas del conjunto de
test (2026-08-24 y 2026-08-25) venían usando el valor de tasa implícita
**arrastrado** del 21-ago en lugar del real de cada día (ej. tasa *front*
real del 24-ago: 32,43%, vs. 26,13% arrastrado) — un problema de frescura de
datos, no un gap de disponibilidad. Se re-descargó el crudo (ahora
2020-01-02 → 2026-11-11, 2.704 filas/41 contratos) y se regeneraron en
cadena `macro.parquet`, `features_long.parquet`,
`features_long_compA.parquet` y `features_long_compC_masked.parquet` a
partir del mismo calendario e índice ya fijados (sin extender el split ni
tocar ninguna otra fuente). Verificado por diff explícito contra las
versiones anteriores: **cambiaron exactamente 2 fechas (24 y 25 de agosto)
en exactamente 3 columnas** (`implied_rate_front`, `implied_rate_next`,
`term_spread_futures`) en los cuatro datasets — ninguna otra fila, columna o
resultado ya reportado se vio afectado (todos los resultados citados en este
proyecto hasta ahora son sobre `val`, nunca sobre `test`). El conteo de
nulos de la tabla de arriba no cambia (no había nulos en esas 2 fechas,
solo valores correctos en lugar de arrastrados).

## 7. Mismas fechas modelo-benchmark, por horizonte

Garantizado por diseño del código, no por disciplina manual: todas las
funciones de evaluación (`naive_zero_metrics`, `pct_vs_naive`,
`compute_variance_metrics`, el cálculo de hit-rate) calculan el benchmark
sobre el mismo array `y_true` que evalúa al modelo — nunca sobre un
subconjunto de fechas distinto. Esto se mantendrá igual para la evaluación
de test; se deja explícito acá porque el director lo pidió como requisito
del protocolo, no porque haya que cambiar algo para cumplirlo.

## Qué falta antes de poder correr esto

1. Aprobación de los directores sobre esta ficha, en particular la decisión
   del punto 3 (reentrenar sobre train+val vs. evaluar el modelo tal cual
   está hoy).
2. Generalizar `walk_forward_evaluate`/`walk_forward_evaluate_variance` para
   aceptar el split "test" (hoy hardcodeadas a "val").
3. Agregar la evaluación sobre test a cada runner de ML/DL (ya soportado
   genéricamente por `split_arrays`/`evaluate`, falta solo la llamada).
4. ~~Resolver (o documentar como no resuelto) el gap de `implied_rate_next`/
   `term_spread_futures` de la sección 6.~~ **[Hecho 6-nov-2026]** Verificado
   contra la API: el gap de `implied_rate_next`/`term_spread_futures` es
   real y no se puede completar (sección 6). De paso se encontró y corrigió
   un problema distinto (datos de futuros arrastrados/stale en las últimas
   2 fechas de test) — ver detalle en sección 6.

Quedan 3 ítems (1-3) antes de poder correr esto — ninguno se ejecuta hasta
tener luz verde sobre el protocolo.
