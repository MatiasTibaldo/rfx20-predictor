# Resultado: GRU + exploración de feature set completo (Bloque 2, Track B, Etapa 2)

**Fecha:** 15 de septiembre de 2026
**Módulos:** `models/deep_learning/gru.py`, `models/deep_learning/gru_runner.py`,
`models/deep_learning/lstm_runner.py` (extendido con `feature_set="full"`),
protocolo compartido generalizado en `models/deep_learning/common.py`
(`prepare_frame`, antes hardcodeado al feature set acotado de Etapa 1).

## Motivación

Etapa 1 (`docs/decisions/lstm_baseline_track_b.md`) dejó un LSTM
prácticamente empatado con el naive usando un feature set deliberadamente
acotado (`log_return` + volatilidad realizada). Etapa 2 responde dos
preguntas abiertas en paralelo:

1. **¿La celda recurrente importa?** — comparar GRU contra el LSTM de
   Etapa 1 con el mismo protocolo exacto (mismo windowing, escalado,
   split de early-stopping, un modelo por horizonte).
2. **¿La complejidad del feature set importa?** — reintroducir el feature
   set completo de Track A ML (indicadores técnicos + macro, 24
   predictores) en ambas arquitecturas, para ver si la falta de señal de
   Etapa 1 se debía al feature set acotado o es un límite más estructural.

## Cambio de diseño: `common.py` generalizado

`build_sequences`, `select_lookback` y `evaluate` ya no reciben
`(df, horizon)` sino `(frame, feature_cols, target_col)`, producidos por
la nueva función `prepare_frame(df, horizon, feature_set)`:

- `feature_set="narrow"` (default, Etapa 1): sin cambios — 4 columnas
  (`log_return`, `realized_vol_10/20/50`) sobre `features_long.parquet` crudo.
- `feature_set="full"` (Etapa 2, nuevo): reutiliza
  `models.ml.common.build_model_frame(df, horizon, exclude_structural_gaps=True)`
  **tal cual la usa SVM** — columnas de precio re-expresadas como ratio a
  close, columnas con gaps estructurales reales (futuros, TAMAR, spreads
  del dólar MEP) **excluidas por completo**, no imputadas. La razón es la
  misma que para SVM: ni LSTM ni GRU aceptan `NaN` en la entrada, y el
  proyecto prohíbe fabricar valores para gaps reales — la alternativa de
  imputar (0, media, forward-fill) queda descartada por la misma regla que
  ya rige Track A ML. Resultado: 24 predictores (vs. 4 en Etapa 1).

Se corrió `lstm_runner.py` con `feature_set="narrow"` (sin cambios de
código) para confirmar que el refactor no alteró el resultado ya
documentado de Etapa 1 — RMSE/MAE idénticos byte a byte.

## Resultado

| Modelo | Feature set | Horizonte | Lookback | RMSE | RMSE naive | MAE | MAE naive |
|---|---|---|---|---|---|---|---|
| LSTM | narrow | 1 | 20 | 0.030011 | 0.029553 | 0.021275 | 0.020782 |
| LSTM | narrow | 3 | 30 | 0.030068 | 0.029531 | 0.021387 | 0.020736 |
| LSTM | narrow | 5 | 10 | 0.029601 | 0.029479 | 0.020856 | 0.020647 |
| GRU  | narrow | 1 | 20 | 0.030207 | 0.029553 | 0.021513 | 0.020782 |
| GRU  | narrow | 3 | 20 | 0.030081 | 0.029531 | 0.021663 | 0.020736 |
| GRU  | narrow | 5 | 20 | 0.030148 | 0.029479 | 0.021465 | 0.020647 |
| LSTM | full   | 1 | 30 | 0.068980 | 0.029553 | 0.061622 | 0.020782 |
| LSTM | full   | 3 | 30 | 0.054863 | 0.029531 | 0.047067 | 0.020736 |
| LSTM | full   | 5 | 30 | 0.060326 | 0.029479 | 0.053230 | 0.020647 |
| GRU  | full   | 1 | 20 | 0.075682 | 0.029553 | 0.068846 | 0.020782 |
| GRU  | full   | 3 | 30 | 0.071396 | 0.029531 | 0.061034 | 0.020736 |
| GRU  | full   | 5 | 30 | 0.063343 | 0.029479 | 0.056384 | 0.020647 |

Predicciones completas en
`results/track_b/{lstm,gru}_val_predictions_h{1,3,5}[_full].parquet`;
tracking en MLflow (experimento `rfx20-track-b`, runs
`{lstm,gru}_h{1,3,5}[_full]`).

## Lectura del resultado

**GRU vs. LSTM (narrow):** prácticamente idénticos entre sí y contra el
naive — la elección de celda recurrente no cambia la conclusión de Etapa
1. No hay evidencia de que GRU capture algo que LSTM no capture, ni
viceversa, con este feature set.

**Feature set completo — degradación clara, no solo empate:** a
diferencia de Etapa 1 (empate con el naive), sumar los 24 predictores de
Track A ML empeora sustancialmente el resultado en ambas arquitecturas
(RMSE 2-2.5x el del naive, en vez de prácticamente igual). Se inspeccionaron
las predicciones (`results/track_b/lstm_val_predictions_h1_full.parquet`)
para descartar un bug: no es un problema de escala ni de fuga — el modelo
converge a una predicción con sesgo sistemático (media ≈ -0.06, desvío
mucho menor al real) que no generaliza a `val`, el patrón clásico de
sobreajuste. Con ~1600 filas de train (menos aún tras las ventanas de
lookback) y 24 features × hasta 30 pasos temporales, la capacidad del
modelo supera ampliamente la señal disponible — el mismo fenómeno que ya
se vio con XGBoost en Track A (`docs/decisions/xgboost_track_a.md`, hasta
61% peor que el naive por sobreajuste sin early stopping), aquí agravado
por la dimensión temporal de las ventanas.

**Conclusión de Etapa 2:** ni cambiar la celda recurrente ni sumar el
feature set completo mejora sobre el naive — de hecho, sumar features sin
más regularización empeora notablemente. El feature set acotado de Etapa
1 queda confirmado como la opción correcta para Track B con esta cantidad
de datos; no se recomienda seguir esta línea (más features, misma
arquitectura simple) sin agregar regularización explícita (dropout, weight
decay) o reducir drásticamente la dimensionalidad (p. ej. PCA sobre los
24 predictores) — fuera del alcance de esta etapa.

## Próximo paso

Evaluación preliminar de TFT/híbrido CNN-LSTM (Track B, Etapa 3) sobre el
feature set **acotado** (narrow) — el que no mostró degradación — salvo
que se decida invertir en regularización para reabrir la línea del
feature set completo.
