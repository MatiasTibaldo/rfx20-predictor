# Resultado: híbrido CNN-LSTM + "TFT-lite" (Bloque 2, Track B, Etapa 3 — cierre del track)

> **Actualización (16 sep 2026):** re-corrido tras el fix de composición de
> sep-2019 (`docs/decisions/sept2019_composicion_corrupta.md`). La
> predicción inestable de TFT-lite en h=5 (nota más abajo, RMSE +18.6%
> peor que naive) se resolvió: ahora +3.5% peor, en línea con el resto de
> horizontes/modelos. CNN-LSTM sin cambios relevantes. No cambia la
> conclusión de síntesis — ver
> `docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`.

**Fecha:** 15 de septiembre de 2026
**Módulos:** `models/deep_learning/cnn_lstm.py` + `cnn_lstm_runner.py`,
`models/deep_learning/tft_lite.py` + `tft_lite_runner.py`.

## Motivación

Etapas 1-2 dejaron LSTM y GRU empatados con el naive sobre el feature set
acotado, y una degradación clara al sumar el feature set completo
(`docs/decisions/lstm_baseline_track_b.md`,
`docs/decisions/track_b_etapa2_gru_full_features.md`). El plan de acción
prevé como paso final y exploratorio de Track B una evaluación preliminar
de TFT/Transformer y de un híbrido CNN-LSTM. Esta etapa cierra el track:
se corren ambas arquitecturas sobre el feature set **acotado** (el que no
mostró degradación), completando así la cobertura de arquitecturas
previstas en el plan antes de pasar a Bloque 3 (comparación y selección).

## Decisión de alcance: "TFT-lite", no TFT completo

Un Temporal Fusion Transformer real (Lim et al., 2019) incluye variable
selection networks, gated residual networks, un encoder de covariables
estáticas y salidas por cuantiles — pensado para escenarios con múltiples
series/entidades y covariables estáticas por entidad. Nada de eso aplica
acá: una sola serie (el índice RFX20), sin covariables estáticas, ~1600
filas de train. El propio plan de acción ya encuadra este punto como
"evaluación preliminar de TFT", no como entregable duro — implementar el
TFT completo sería desproporcionado para lo que se puede aprender con
este dataset y, sobre todo, sería una sobre-ingeniería dado el patrón ya
consistente de Etapas 1-2.

Se implementó en cambio `TFTLiteRegressor`
(`models/deep_learning/tft_lite.py`): proyección lineal de los features de
entrada + encoding posicional sinusoidal + un `TransformerEncoderLayer` de
PyTorch (atención multi-cabeza) + cabeza lineal. Toma de TFT el
ingrediente más relevante para esta pregunta puntual (atención en vez de
una celda recurrente) y nada más — se documenta explícitamente como una
aproximación reducida, no como una reproducción del paper original, para
que la tesis no sobre-represente lo que se implementó.

El híbrido CNN-LSTM (`CNNLSTMRegressor`) sí es una arquitectura estándar
sin reducción de alcance: una capa `Conv1d` (extracción de patrones
locales sobre el eje temporal) seguida de una LSTM.

Ambas reutilizan el protocolo exacto de Etapas 1-2 (windowing, escalado,
split de early-stopping, un modelo por horizonte, lookback por grid
search `{10,20,30}` contra early-stopping, nunca contra `val`).

## Resultado

| Modelo | Horizonte | Lookback | RMSE | RMSE naive | MAE | MAE naive |
|---|---|---|---|---|---|---|
| CNN-LSTM | 1 | 20 | 0.030054 | 0.029553 | 0.021347 | 0.020782 |
| CNN-LSTM | 3 | 10 | 0.030097 | 0.029531 | 0.021206 | 0.020736 |
| CNN-LSTM | 5 | 20 | 0.029886 | 0.029479 | 0.021139 | 0.020647 |
| TFT-lite | 1 | 30 | 0.030200 | 0.029553 | 0.021630 | 0.020782 |
| TFT-lite | 3 | 30 | 0.029936 | 0.029531 | 0.021260 | 0.020736 |
| TFT-lite | 5 | 10 | 0.034975 | 0.029479 | 0.022321 | 0.020647 |

Predicciones en
`results/track_b/{cnn_lstm,tft_lite}_val_predictions_h{1,3,5}.parquet`;
MLflow experimento `rfx20-track-b`, runs `cnn_lstm_h{1,3,5}` / `tft_lite_h{1,3,5}`.

**Nota sobre TFT-lite, h=5:** el RMSE (0.034975, ~19% peor que el naive)
es engañoso si se lo mira solo — el MAE (0.022321) está mucho más cerca
del naive (0.020647, ~8% peor). Se inspeccionaron las 294 predicciones de
val: una sola ventana (ancla 2025-10-27) produjo una predicción extrema
(-0.2776) frente a un valor real apenas positivo (+0.0326); el resto de
las predicciones se agrupa en el mismo rango angosto cercano a cero que
el resto de las arquitecturas (percentiles 25-75% entre 0.0015 y 0.0065).
Es decir, no es un sesgo sistemático como el de Etapa 2 con el feature
set completo — es una única extrapolación inestable, típica de modelos
de mayor capacidad (atención) entrenados con muy pocos datos, y el RMSE
(que penaliza cuadráticamente) la amplifica más que el MAE.

## Lectura del resultado

CNN-LSTM y TFT-lite completan el mismo patrón que LSTM y GRU: ninguna
arquitectura de Track B, con el feature set acotado, mejora sobre el
naive. Sumando ARIMA/SARIMA, SVM, RF, XGBoost, LightGBM, LSTM, GRU,
CNN-LSTM y TFT-lite son **nueve métodos independientes** —de tres
paradigmas distintos (estadístico, ML clásico, deep learning) y ahora
incluyendo tanto una arquitectura convolucional como una basada en
atención— que coinciden en que la dirección del retorno diario del RFX20
no es pronosticable con la información disponible. La consistencia a
través de nueve métodos con supuestos y capacidades muy distintas es en sí
misma el hallazgo central de Bloque 2: no es un problema de arquitectura,
es una ausencia estructural de señal explotable en la media condicional
del retorno con este conjunto de datos. Ver
`docs/decisions/track_a_b_sintesis_direccion_volatilidad.md` para el
detalle completo de los nueve métodos y su contraste con el resultado
positivo de GARCH.

## Cierre de Track B

Con esta etapa, Track B queda completo: LSTM, GRU, CNN-LSTM y "TFT-lite"
evaluados con protocolo comparable, sobre el feature set acotado como
elección justificada (Etapa 2 mostró que sumar features degrada, no solo
empata). Bloque 2 (Track A + Track B) cierra con dos hallazgos: (1)
dirección no pronosticable — diez métodos independientes coinciden; (2)
volatilidad condicional sí pronosticable — GARCH, ~39-40% mejor que el
naive. Ver `docs/decisions/track_a_b_sintesis_direccion_volatilidad.md`
para la síntesis completa de Bloque 2 antes de pasar a Bloque 3
(comparación y selección de modelo final).
