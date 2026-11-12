Ficha de protocolo — evaluación final (resumen)

**Conjunto de test**: 2026-04-20 → 2026-08-25, 86 fechas (100% fuera de
muestra, nunca usado en ninguna decisión de desarrollo). N efectivo por
horizonte: 85 (h=1) / 83 (h=3) / 81 (h=5) — se achica por el target que mira
hacia adelante.

**Modelos**: los 10 oficiales de Bloque 2 (ARIMA/SARIMA, GARCH, SVM, RF,
XGBoost, LightGBM, LSTM, GRU, CNN-LSTM, Transformer encoder), mismos
hiperparámetros/arquitectura ya elegidos sobre train/val — no se vuelve a
buscar nada sobre test.

**Actualización durante el período**:
- ARIMA/GARCH: walk-forward diario, igual que en validación (orden fijo,
  coeficientes reestimados cada día).
- Resto de los modelos: **punto a definir con ustedes** — reentrenar una vez
  sobre train+val combinado antes de evaluar sobre test (nuestra propuesta,
  usa toda la información disponible), o evaluar el modelo tal como está
  documentado hoy (alternativa más conservadora, sin reentrenar).

**Benchmarks**: retorno → naive de retorno cero; dirección → 50% y "mayoría
de train" (agregado por su pedido); volatilidad → naive de varianza
constante y EWMA.

**Métricas**: RMSE/MAE + N efectivo (retorno); hit-rate + test binomial
contra ambos benchmarks (dirección); RMSE/QLIKE (volatilidad); intervalo de
confianza 95% por bootstrap de bloques para cada comparación, individual, no
conjunto.

**Predictores**: confirmado — 2 columnas (`implied_rate_next`,
`term_spread_futures`) tienen gaps reales en ~1/3 de las fechas de test,
mismo tratamiento ya usado en todo el proyecto (nulo real para árboles,
exclusión para SVM/redes). Re-chequeado contra la API de MatbaRofex: el gap
es real (esos días solo cotizó un contrato), no se puede completar. De paso
encontramos y corregimos un problema distinto: los últimos dos días de test
(24 y 25 de agosto) tenían un valor de tasa implícita desactualizado
(arrastrado del 21-ago, por no haber re-descargado los datos de futuros
desde esa fecha) — ya corregido con datos reales de esos días.

**Mismas fechas modelo-benchmark**: garantizado por el código, cada
comparación usa exactamente el mismo conjunto de fechas para el modelo y su
referencia.

Detalle técnico completo en `docs/decisions/ficha_protocolo_evaluacion_final.md`
del repositorio. Quedamos atentos a la reunión para cerrar el punto de
actualización de modelos antes de correr el test.
