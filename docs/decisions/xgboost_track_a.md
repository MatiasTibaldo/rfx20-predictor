# Resultado: XGBoost (Bloque 2, Track A ML, Etapa 3)

**Fecha:** 5 de septiembre de 2026
**Módulo:** `models/ml/xgboost_runner.py` (protocolo compartido en `models/ml/common.py`)
**Dependencia agregada:** `xgboost` (`uv add xgboost`) — nota: arrastra
`nvidia-nccl-cu12` (326MB) como dependencia del paquete de PyPI aunque el
proyecto es CPU-only (sin GPU); no afecta la ejecución, XGBoost usa
`tree_method="hist"` sobre CPU, solo ocupa espacio en disco.

## Protocolo

Mismo protocolo que Random Forest (ver `docs/decisions/rf_track_a.md` y
`docs/decisions/ml_feature_engineering_track_a.md`): 30 columnas completas,
incluidas las de futuros/TAMAR/MEP con sus nulos reales (XGBoost las maneja
de forma nativa). Hiperparámetros buscados: `n_estimators`, `max_depth`,
`learning_rate`, `subsample`, `colsample_bytree`, `reg_lambda`
(regularización L2), vía `RandomizedSearchCV` (20 iteraciones) sobre
`TimeSeriesSplit` (5 folds) en train.

## Resultado

| Horizonte | RMSE XGBoost | RMSE naive (predice 0) | MAE XGBoost | MAE naive |
|---|---|---|---|---|
| 1 | 0.047511 | 0.029553 | 0.029790 | 0.020782 |
| 3 | 0.041812 | 0.029531 | 0.025297 | 0.020736 |
| 5 | 0.031162 | 0.029479 | 0.021668 | 0.020647 |

A diferencia de SVM (empatado) y Random Forest (levemente peor), XGBoost
queda **sustancialmente peor** que el naive en los tres horizontes —
~61% más RMSE en h=1, ~42% en h=3, ~6% en h=5 (la brecha se achica con el
horizonte, consistente con menos capacidad de sobreajustar un target más
lejano y más ruidoso). Las importancias por permutación tampoco son
estables entre horizontes (`bb_high_rel`/`realized_vol_50` en h=1,
`realized_vol_50`/`log_return` en h=3, `macd_signal`/`macd` en h=5).

## Lectura del resultado

Es un patrón de **sobreajuste**, no evidencia de que XGBoost sea
"peor modelo" en abstracto: sobre un dataset relativamente chico (1611
filas de train) y con un target dominado por ruido (ya establecido por
ARIMA/SVM/RF), un método de boosting con suficiente capacidad encuentra
estructura espuria en train que no generaliza a val, incluso con
regularización L2 buscada explícitamente por CV. Esto es consistente con
la literatura de forecasting financiero: los métodos de boosting suelen
requerir *early stopping* explícito (deteniendo el entrenamiento cuando la
métrica de validación deja de mejorar, no solo buscar `n_estimators` como
un hiperparámetro más) para controlar este efecto, algo que este baseline
no implementó — se mantiene fuera de alcance acá para no romper la
comparabilidad del protocolo de CV ya fijado para las 4 familias de
modelos, y se deja como ajuste a evaluar en Bloque 3 si XGBoost llegara a
ser candidato para el ensemble final.

**No se ajustó manualmente la regularización para mejorar el número** —
el resultado se reporta tal como salió de la búsqueda por CV, en línea con
mantener el protocolo replicable y no sesgado por intervención post-hoc.
