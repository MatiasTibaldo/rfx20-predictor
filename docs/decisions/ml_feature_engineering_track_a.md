# Decisión: feature engineering y protocolo de validación para ML clásico (Bloque 2, Track A)

**Fecha:** 5 de septiembre de 2026
**Módulos:** `models/ml/common.py` y los runners por modelo (`svm_runner.py`,
`rf_runner.py`, `xgboost_runner.py`, `lightgbm_runner.py`).

## Contexto

Con el baseline ARIMA/SARIMA + GARCH cerrado (ver
`docs/decisions/arima_baseline_track_a.md` y
`docs/decisions/garch_volatility_track_a.md`), Track A continúa con SVM,
Random Forest, XGBoost y LightGBM. A diferencia de ARIMA/GARCH (univariados,
solo la propia serie del índice), estos modelos son multivariados: consumen
todo `features_long.parquet` como predictores. El alumno pidió explícitamente
que estos modelos sean **robustos, replicables y fáciles de explicar** — ver
[[feedback_model_explainability]] — lo que fija varias decisiones de diseño
compartidas por los cuatro modelos, documentadas acá una sola vez.

## Decisión 1 — Un modelo por horizonte, mismo feature set base

Se entrena un modelo independiente por horizonte (`h ∈ {1,3,5}`) y por
algoritmo, en vez de un único modelo multi-output. Es más fácil de explicar
("este modelo predice h=1, con estas variables y esta importancia") y
consistente con cómo ya se reportó ARIMA/GARCH. El feature set base es
`features_long.parquet` completo (índice + macro, ya consolidado en Nodo 4),
sin volver a traer los 27 componentes — ninguno de estos cuatro modelos lo
requiere todavía, mismo criterio que ya fijó
`docs/decisions/temporal_split_and_consolidation.md`.

## Decisión 2 — Indicadores de nivel de precio, re-expresados como ratios

`ma_10`, `ma_20`, `ma_50`, `bb_high`, `bb_low`, `bb_mid` están en la escala
del precio del índice (que pasó de ~30.000 a niveles muy superiores a lo
largo de 2018-2026, por inflación/devaluación) — alimentarlos como nivel
crudo a un modelo de ML introduciría una tendencia no estacionaria ajena a
la señal real que esos indicadores buscan capturar, y es particularmente
grave para SVM (sensible a escala/distancia). Se re-expresan como razón
relativa al cierre del mismo día antes de entrenar (ej. `ma_10_rel =
ma_10/close - 1`, análogamente para `bb_high`/`bb_low`/`bb_mid`), y se
descartan las columnas crudas (incluida `close`) del feature set. El resto
de los indicadores (`rsi_14`, `macd*`, `realized_vol_*`, spreads, tasas)
ya son adimensionales o porcentuales y se usan tal cual. Esta
transformación ocurre en la etapa de modelado (`models/ml/common.py`), no
en `features/` — no reabre el Nodo 4, que ya cerró (Bloque 1).

## Decisión 3 — Nunca imputar datos faltantes; usar manejo nativo de nulos o excluir

Ver [[feedback_no_impute_missing_data]] para el principio general. El caso
concreto que lo disparó: `implied_rate_front`, `implied_rate_next`,
`term_spread_futures` son nulos en ~30% de train — un tramo estructural
(sin datos de futuros en la API antes de 2020-01-02, aunque el mercado ya
operaba desde agosto de 2019 según documentación adicional del alumno,
pendiente de anexar la circular — ver
`docs/decisions/futures_implied_rate.md`) y un patrón disperso mecánico
(la tasa implícita se vuelve nula justo en el rolado de contrato, donde la
fórmula `r=(F/S)^(365/t)-1` se indefine con `t→0`; confirmado con el
historial completo de `RFX20032020`, cuya última rueda fue el 2020-03-30 —
31/03 feriado).

Se rechazó imputar 0 o la mediana de train: un valor inventado quedaría
mezclado entre observaciones reales de 10%-150% y el modelo lo trataría
como una tasa real, no como "sin dato". Resolución adoptada, verificada
contra la versión instalada de cada librería:

| Modelo | Maneja NaN nativamente | Resolución |
|---|---|---|
| Random Forest (`scikit-learn` 1.8.0) | Sí, confirmado empíricamente (`RandomForestRegressor.fit` con NaN no falla) | Recibe las 3 columnas con sus nulos reales, sin imputar |
| XGBoost | Sí (manejo nativo de sparsity/missing) | Ídem |
| LightGBM | Sí (`use_missing=True` por default) | Ídem |
| SVM (`sklearn.svm.SVR`) | No — requiere matriz completa | **Excluye las 3 columnas de futuros de su feature set.** No se imputa ni se recorta el dataset; simplemente ese modelo no usa esas variables |

Se agrega además una columna binaria `futures_available` (1 si las tres
columnas tienen dato ese día, 0 si no) a los tres modelos de árbol —
redundante con el patrón de nulos que ya ven, pero deja explícito en el
reporte de importancia de variables si la disponibilidad de dato de
futuros es en sí misma relevante para el modelo.

## Decisión 4 — Selección de hiperparámetros: CV temporal expansiva, no un solo corte

Para elegir hiperparámetros de cada modelo se usa `TimeSeriesSplit` (varios
folds expansivos) sobre el split `train`, dentro de una búsqueda acotada
(`RandomizedSearchCV`, `n_iter` fijo, `scoring="neg_root_mean_squared_error"`,
`random_state` fijo para replicabilidad exacta). El split `val` no participa
de la búsqueda — se usa, igual que en ARIMA/GARCH, solo para evaluar una vez
el modelo ya elegido, manteniendo el mismo protocolo de comparación entre
las cuatro familias de modelos de Track A. El split `test` no se toca (queda
para Bloque 3).

## Decisión 5 — Importancia de variables uniforme: permutation importance

Para que la explicabilidad sea comparable entre los cuatro modelos (RF/XGBoost/
LightGBM exponen importancia nativa con distintas semánticas entre sí; SVM no
expone ninguna), se calcula *permutation importance* sobre el split `val`
para los cuatro, con semilla fija. Es el único método de importancia que
aplica igual a cualquier estimador, lo que permite comparar qué variables
pesan más en cada familia de modelo con el mismo criterio.

## Pendiente

Construir `models/ml/common.py` (matriz de features, protocolo de CV,
permutation importance, métricas) y los cuatro runners, en ese orden: SVM,
Random Forest, XGBoost, LightGBM — validando cada uno antes de avanzar al
siguiente (mismo criterio de etapas ya usado en Nodo 4 y en Track A
Etapas 1-2).
