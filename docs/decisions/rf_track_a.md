# Resultado: Random Forest (Bloque 2, Track A ML, Etapa 2)

**Fecha:** 5 de septiembre de 2026
**Módulo:** `models/ml/rf_runner.py` (protocolo compartido en `models/ml/common.py`)

## Protocolo

Mismo protocolo que SVM (ver `docs/decisions/svm_track_a.md` y
`docs/decisions/ml_feature_engineering_track_a.md`): un modelo por
horizonte, `RandomizedSearchCV` (20 iteraciones) sobre `TimeSeriesSplit`
(5 folds) en train, evaluación única en val, permutation importance.
Diferencia clave: `RandomForestRegressor` (scikit-learn 1.8.0) acepta NaN
de forma nativa (confirmado empíricamente antes de decidir el protocolo,
ver `docs/decisions/ml_feature_engineering_track_a.md`), así que recibe las
30 columnas completas — incluidas `implied_rate_front/next`,
`term_spread_futures`, `tamar`, `spread_oficial_mep`, `spread_mep_ccl` con
sus nulos reales, sin excluir nada (a diferencia de SVM, que usó 24
columnas). Hiperparámetros buscados: `n_estimators`, `max_depth`,
`min_samples_leaf`, `max_features`.

## Resultado

| Horizonte | RMSE RF | RMSE naive (predice 0) | MAE RF | MAE naive |
|---|---|---|---|---|
| 1 | 0.030066 | 0.029553 | 0.021160 | 0.020782 |
| 3 | 0.029830 | 0.029531 | 0.021113 | 0.020736 |
| 5 | 0.029484 | 0.029479 | 0.020950 | 0.020647 |

Random Forest queda **levemente peor** que el naive en los tres
horizontes, en ambas métricas — más que SVM (que había quedado
prácticamente empatado). Las importancias por permutación top-5 no son
estables entre horizontes:

- h=1: `realized_vol_50`, `tasa_pf`, `rsi_14`, `simple_return`, `log_return`
- h=3: `log_return`, `simple_return`, `implied_rate_front`, `tasa_pf`, `realized_vol_20`
- h=5: `macd_diff`, `macd_signal`, `ma_50_rel`, `realized_vol_20`, `macd`

Ningún feature se repite consistentemente como top-1 entre los tres
horizontes, y las magnitudes son pequeñas (1e-5 a 1e-4) — más compatible
con ruido de la búsqueda de hiperparámetros que con una señal genuina y
estable.

## Lectura del resultado

Tercera confirmación independiente (tras ARIMA y SVM) de que no hay señal
explotable en la media condicional del retorno diario del índice con este
feature set. A diferencia de SVM (kernel RBF), Random Forest puede capturar
interacciones no lineales y splits arbitrarios sobre variables categóricas
de disponibilidad (`futures_available`, etc.) — que tampoco encuentre nada
mejor que el naive refuerza el hallazgo en lugar de debilitarlo. Queda
XGBoost y LightGBM para completar el panorama de Track A antes de la
conclusión definitiva sobre la media condicional en la tesis.
