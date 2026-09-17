# Resultado: LSTM baseline (Bloque 2, Track B, Etapa 1)

**Fecha:** 15 de septiembre de 2026
**Módulo:** `models/deep_learning/lstm_runner.py` (protocolo compartido en
`models/deep_learning/common.py`, arquitectura en `models/deep_learning/lstm.py`)

## Motivación

Track A (Bloque 2) cerró con seis métodos independientes (ARIMA/SARIMA,
GARCH, SVM, Random Forest, XGBoost, LightGBM) coincidiendo en que la
**dirección** del retorno diario del RFX20 no es pronosticable con el
feature set de indicadores técnicos + macro, en los horizontes 1/3/5 días
(ver `docs/decisions/xgboost_track_a.md`, `svm_track_a.md`, `rf_track_a.md`,
`lightgbm_track_a.md`, `arima_baseline_track_a.md`). El plan de acción
indica Track B (Deep Learning) como siguiente paso: arquitecturas capaces
de modelar dependencia secuencial explícita que ninguno de los modelos de
Track A intenta (los de árbol/SVM tratan cada fila como independiente;
ARIMA solo modela autocorrelación lineal). Esta etapa es el primer
baseline — LSTM simple — antes de sumar GRU y la evaluación preliminar de
TFT/híbrido CNN-LSTM en etapas siguientes.

## Decisiones de diseño (confirmadas antes de implementar)

1. **Feature set deliberadamente acotado:** `log_return` +
   `realized_vol_10/20/50` — sin macro, sin indicadores técnicos (RSI,
   MACD, Bollinger). A diferencia de Track A ML (24+ predictores), este
   baseline usa 4 columnas. Razón: aislar si la arquitectura secuencial
   por sí sola aporta algo sobre la señal más simple posible, antes de
   pagar el costo de complejidad (más parámetros, más riesgo de
   sobreajuste) de sumar macro — la misma lógica de "construir por
   etapas validadas" que ya se usó en Bloque 1.
2. **Un modelo por horizonte** (1, 3, 5 días), igual que Track A —
   comparabilidad directa de RMSE/MAE contra ARIMA/SVM/RF/XGBoost/
   LightGBM/GARCH sin tener que normalizar por una arquitectura
   multi-output distinta.
3. **Windowing:** ventanas deslizantes de `lookback` días construidas
   sobre la serie completa (`features_long.parquet`, los tres splits
   juntos) — una ventana de val/test puede mirar hacia atrás dentro de
   filas de train (son valores pasados reales, no fuga de información;
   misma lógica que el warm-up de indicadores técnicos al inicio de
   train). El split de la fila ancla (última fila de la ventana)
   determina a qué split pertenece esa ventana.
4. **Lookback como hiperparámetro elegido empíricamente:** grid chico
   `{10, 20, 30}` por horizonte (anclado a las ventanas de MA/volatilidad
   ya usadas en el proyecto), seleccionado por pérdida de
   early-stopping — **nunca por `val`**.
5. **Escalado:** `StandardScaler` (igual patrón que el `Pipeline` de
   `svm_runner.py`) ajustado solo sobre las ventanas de la porción de
   train usada para entrenar (`train_fit`), aplicado a `train_earlystop`,
   `val` y `test`.
6. **Split de early stopping:** el 15% cronológicamente más reciente de
   train se reserva como `train_earlystop` (nunca se usa `val` para
   parar el entrenamiento ni para elegir el lookback) — preserva el
   mismo principio que Track A ML: `val` es una comparación limpia, no
   vista durante ningún paso de selección de modelo.
7. **Protocolo de evaluación:** entrenamiento único con early stopping +
   una sola evaluación sobre `val` (no refit diario tipo ARIMA/GARCH —
   reentrenar una red cada día del walk-forward sería computacionalmente
   injustificado para este baseline).
8. **Arquitectura:** LSTM de una capa, `hidden_size=32`, sin atención ni
   bidireccionalidad — la comparación con GRU/TFT/híbrido queda para
   etapas siguientes. Sin búsqueda de hiperparámetros de arquitectura en
   esta etapa (solo el lookback) — mismo principio de acotar el alcance
   del primer baseline.

## Dependencia

`torch` (CPU-only, extra `[cpu]` ya declarado en `pyproject.toml` desde el
inicio del proyecto, sin sincronizar hasta ahora): `uv sync --extra cpu`
(torch 2.11.0+cpu).

## Resultado

| Horizonte | Lookback elegido | RMSE LSTM | RMSE naive (predice 0) | MAE LSTM | MAE naive |
|---|---|---|---|---|---|
| 1 | 20 | 0.030011 | 0.029553 | 0.021275 | 0.020782 |
| 3 | 30 | 0.030068 | 0.029531 | 0.021387 | 0.020736 |
| 5 | 10 | 0.029601 | 0.029479 | 0.020856 | 0.020647 |

En los tres horizontes, la pérdida de early-stopping mejora solo en las
primeras 1-8 épocas (ver runs en MLflow, experimento `rfx20-track-b`) y
queda prácticamente idéntica al MSE del naive (predecir retorno 0) — la
red converge rápido a predicciones cercanas a cero/la media incondicional
y no encuentra estructura adicional que reduzca la pérdida más allá de
eso. En `val`, el LSTM queda levemente peor que el naive en los tres
horizontes (diferencia de tercer/cuarto decimal, dentro del ruido, mismo
orden de magnitud que SVM y Random Forest).

Predicciones completas por horizonte en
`results/track_b/lstm_val_predictions_h{1,3,5}.parquet`; tracking de
hiperparámetros y métricas en MLflow (`mlruns.db`, experimento
`rfx20-track-b`, runs `lstm_h1`/`lstm_h3`/`lstm_h5`).

## Lectura del resultado

Séptima confirmación independiente (tras ARIMA/SARIMA, GARCH probando lo
contrario para volatilidad, SVM, Random Forest, XGBoost, LightGBM) de que
la dirección del retorno diario del RFX20 no es pronosticable con la
información disponible — esta vez con una arquitectura que sí modela
dependencia secuencial explícita, y sobre un feature set más simple aún
que el de Track A ML. El resultado negativo es consistente con la
hipótesis de que el problema no es la falta de una arquitectura adecuada
sino la ausencia de señal explotable en la media condicional del retorno
en este mercado con este conjunto de datos.

## Próximo paso

GRU (mismo protocolo, arquitectura alternativa) y evaluación preliminar de
TFT/híbrido CNN-LSTM — Track B, Etapa 2. Evaluar en esa etapa si vale la
pena reintroducir el feature set completo (macro + técnicos) dado que el
baseline univariado no mostró ninguna ventaja que justifique mantenerlo
acotado.
