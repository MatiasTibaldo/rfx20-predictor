# Resultado: SVM (Bloque 2, Track A ML, Etapa 1)

**Fecha:** 5 de septiembre de 2026
**Módulo:** `models/ml/svm_runner.py` (protocolo compartido en `models/ml/common.py`)

## Protocolo

Ver `docs/decisions/ml_feature_engineering_track_a.md` para el detalle
completo del protocolo compartido por los cuatro modelos de ML de Track A
(feature set, CV temporal, permutation importance). Específico de SVM:
`SVR` con kernel RBF dentro de un `Pipeline` con `StandardScaler` (SVM es
sensible a escala); búsqueda de `C`, `gamma`, `epsilon` por
`RandomizedSearchCV` (20 iteraciones, distribuciones log-uniformes) sobre
`TimeSeriesSplit` (5 folds) en train. Al no aceptar NaN, excluye del
feature set las columnas con gaps estructurales reales (futuros, TAMAR,
spreads del dólar MEP — ver Decisión 3 del documento de feature
engineering), quedándose con 24 predictores (train=1611 filas tras
descartar el warm-up de indicadores técnicos, val=294).

## Bug encontrado durante la implementación

La primera corrida dejó train en **81 filas** (de 1661): el filtro de
"descartar filas con cualquier nulo" no contemplaba que `tamar` (1580
nulos en train — la serie arranca en oct-2024) y `spread_oficial_mep`/
`spread_mep_ccl` (142 nulos — el dólar MEP arranca 2018-10-29) son gaps
estructurales del mismo tipo que ya se había resuelto para futuros, pero
no se habían generalizado en el código. Se corrigió extendiendo el mismo
criterio (exclusión para SVM, nulos reales para los modelos de árbol) a
estas columnas — ver Decisión 3 actualizada en
`docs/decisions/ml_feature_engineering_track_a.md`.

## Resultado

| Horizonte | RMSE SVM | RMSE naive (predice 0) | MAE SVM | MAE naive |
|---|---|---|---|---|
| 1 | 0.029653 | 0.029553 | 0.021008 | 0.020782 |
| 3 | 0.029621 | 0.029531 | 0.020927 | 0.020736 |
| 5 | 0.029422 | 0.029479 | 0.020638 | 0.020647 |

SVM queda prácticamente empatado con el baseline naive — levemente peor en
h=1 y h=3, levemente mejor en h=5 (diferencia de cuarto decimal, dentro del
ruido). Las importancias por permutación son casi nulas en los tres
horizontes (orden de 1e-6 a 1e-4), sin ningún feature destacándose de forma
consistente entre horizontes.

## Lectura del resultado

Consistente con el hallazgo de ARIMA (`docs/decisions/arima_baseline_track_a.md`):
tampoco un modelo no lineal (kernel RBF) con un feature set multivariado
(técnicos + macro) encuentra estructura explotable en la media condicional
del retorno. Es la segunda confirmación independiente, con un método
distinto, de que la dirección del retorno diario del índice no es
pronosticable con esta información — refuerza que el foco de valor
predictivo en Track A sigue estando del lado de la volatilidad (GARCH), no
de la dirección. Random Forest/XGBoost/LightGBM (próximas etapas)
completan el panorama antes de sacar una conclusión definitiva sobre la
media condicional en la sección de resultados de la tesis.
