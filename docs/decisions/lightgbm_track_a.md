# Resultado: LightGBM (Bloque 2, Track A ML, Etapa 4 — cierra Track A)

**Fecha:** 5-6 de septiembre de 2026
**Módulo:** `models/ml/lightgbm_runner.py` (protocolo compartido en `models/ml/common.py`)
**Dependencia agregada:** `lightgbm` (`uv add lightgbm`, 3.3MB, sin dependencias GPU).

## Protocolo

Mismo protocolo que Random Forest y XGBoost (ver
`docs/decisions/ml_feature_engineering_track_a.md`): 30 columnas completas,
incluidas futuros/TAMAR/MEP con nulos reales (`use_missing=True` por
default en LightGBM). Hiperparámetros buscados: `n_estimators`, `max_depth`,
`num_leaves`, `learning_rate`, `subsample`, `colsample_bytree`,
`reg_lambda`, `min_child_samples`, vía `RandomizedSearchCV` (20
iteraciones) sobre `TimeSeriesSplit` (5 folds) en train.

## Bug de performance encontrado (no afecta el resultado, sí el tiempo de corrida)

Cada horizonte tardó entre 2 y 2.5 horas (~7 horas en total), frente a
segundos en XGBoost y ~1.5 minutos en Random Forest sobre el mismo dataset
y el mismo protocolo de búsqueda. Causa: `LGBMRegressor(n_jobs=-1)` y
`RandomizedSearchCV(n_jobs=-1)` paralelizan al mismo tiempo en dos niveles
— cada uno de los ~20 fits en paralelo de la búsqueda intentaba además usar
todos los cores disponibles internamente para el propio boosting,
generando sobre-suscripción masiva de threads (cientos de threads
compitiendo por los ~14-16 cores reales de la máquina). Es un pitfall
documentado de combinar LightGBM con herramientas de paralelización de
`scikit-learn`. Se corrigió fijando `n_jobs=1` en `LGBMRegressor` (deja
que `RandomizedSearchCV` sea el único nivel que paraleliza) — no se
volvió a correr el experimento completo porque el resultado ya obtenido es
válido (el bug afecta tiempo de cómputo, no el resultado numérico); el fix
queda para que una corrida futura (ej. si se ajusta la grilla de
hiperparámetros) no vuelva a tardar horas.

## Resultado

| Horizonte | RMSE LightGBM | RMSE naive (predice 0) | MAE LightGBM | MAE naive |
|---|---|---|---|---|
| 1 | 0.030829 | 0.029553 | 0.021730 | 0.020782 |
| 3 | 0.029423 | 0.029531 | 0.020673 | 0.020736 |
| 5 | 0.029970 | 0.029479 | 0.021764 | 0.020647 |

LightGBM queda levemente peor que el naive en h=1 y h=5, y marginalmente
mejor (cuarto decimal) en h=3 — sin mejora significativa en ningún
horizonte. A diferencia de XGBoost, no muestra el mismo patrón de
sobreajuste severo, más en línea con SVM y Random Forest. Importancias por
permutación, sin patrón estable entre horizontes: `rsi_14`/`realized_vol_50`
en h=1, `term_spread_futures`/`realized_vol_50` en h=3,
`macd_diff`/`spread_oficial_mep` en h=5.

## Lectura del resultado y síntesis de Track A ML (SVM, RF, XGBoost, LightGBM)

Cuarta confirmación de que no hay señal explotable en la media condicional
del retorno diario del índice con este feature set — consistente en las
cuatro familias de modelos de ML clásico, y consistente también con el
resultado de ARIMA/SARIMA (Bloque 2, Etapa 1). El único modelo que se
apartó de este patrón fue XGBoost, y por sobreajuste (peor que el naive),
no por encontrar señal real.

**Síntesis para la tesis:** con seis métodos independientes (ARIMA/SARIMA,
SVM, Random Forest, XGBoost, LightGBM, más el resultado de GARCH que ataca
una pregunta distinta), la dirección del retorno diario del RFX20 no
resulta pronosticable a partir de su propio historial técnico y de
variables macro contemporáneas/rezagadas, dentro de los horizontes de 1, 3
y 5 días hábiles evaluados. Esto no invalida el proyecto: motiva
explícitamente explorar si Deep Learning (Track B — LSTM/GRU, con
capacidad de capturar dependencias no lineales de más largo plazo o
representaciones más ricas de la serie) encuentra algo que los métodos
estadísticos y de ML clásico no encontraron, y refuerza que el resultado
positivo de GARCH (volatilidad condicional) es el hallazgo central de
Bloque 2 hasta el momento.

## Cierre de Bloque 2 - Track A

Con esto se completan los 4 modelos de ML clásico del plan de acción
(SVM, Random Forest, XGBoost, LightGBM), sumados a ARIMA/SARIMA + GARCH.
Track A (estadístico + ML clásico) queda completo. Pendiente: Track B
(Deep Learning — LSTM, GRU, evaluación preliminar de TFT/híbrido CNN-LSTM),
en paralelo según el plan de acción, y Bloque 3 (comparación y selección
multicriterio, incluyendo estos 6 resultados de Track A).
