# Notas de sesión — 5 al 8 de septiembre de 2026

Nota interna de trabajo con Claude Code, no un documento para los directores
(eso es `avance_trabajo_final.md`). Sirve como bitácora rápida de qué se
hizo y en qué orden — el detalle metodológico completo de cada punto está
en su propio archivo de `docs/decisions/`, referenciado abajo.

## Qué se hizo

1. **Checkpoint 1 redactado** — `avance_trabajo_final.md` actualizado a
   Versión 2, incorporando la metodología de Fase 2 (features).
2. **Track A, Bloque 2 — completo:**
   - ARIMA/SARIMA baseline → `docs/decisions/arima_baseline_track_a.md`
   - GARCH → `docs/decisions/garch_volatility_track_a.md`
   - Protocolo compartido de ML (SVM/RF/XGBoost/LightGBM) →
     `docs/decisions/ml_feature_engineering_track_a.md`
   - SVM → `docs/decisions/svm_track_a.md`
   - Random Forest → `docs/decisions/rf_track_a.md`
   - XGBoost → `docs/decisions/xgboost_track_a.md`
   - LightGBM → `docs/decisions/lightgbm_track_a.md`
   - Extensión a horizontes largos (10/21 días) — evaluada y descartada →
     `docs/decisions/long_horizons_track_a.md`
3. **Migración de MLflow** de backend de archivos (`mlruns/`, en
   mantenimiento desde MLflow 3.15) a SQLite (`mlruns.db`).
4. **Corrección de documentación desactualizada**: la nota sobre ECOG en
   `docs/decisions/rfx20_ws_backfill.md` y `avance_trabajo_final.md` decía
   que faltaba incorporar su ingesta — ya estaba resuelto, solo el texto
   había quedado atrasado.
5. **Commit + push** de todo lo anterior (lo hizo el alumno directamente).

## Hallazgo central de Track A

Seis métodos (ARIMA/SARIMA, SVM, Random Forest, XGBoost, LightGBM, GARCH),
evaluados en cinco horizontes (1, 3, 5, 10, 21 días hábiles): la
**dirección** del retorno diario del RFX20 no es pronosticable con el
feature set actual en ningún horizonte probado. La **volatilidad
condicional** (GARCH) sí tiene estructura explotable y de forma consistente
(~39-40% menos error de varianza que el naive) en todos los horizontes.

## Bugs encontrados y corregidos en el camino

- `models/ml/common.py` descartaba `date`/`split` junto con las columnas
  que no correspondía (bug de una sola corrida, detectado enseguida).
- Gaps estructurales de TAMAR y dólar MEP no estaban contemplados en el
  filtro de nulos — dejaban el train de SVM en 81 filas en vez de 1611.
- LightGBM + `RandomizedSearchCv` con `n_jobs=-1` en ambos niveles generó
  sobre-suscripción de threads (~7h en vez de minutos) — corregido.
- Bug de fuga potencial: la lista de columnas `log_return_fwd_*` a excluir
  estaba hardcodeada a 1/3/5: con el dataset extendido a 10/21,
  `log_return_fwd_10/21` se hubieran colado como features. Corregido con
  detección dinámica por prefijo — queda como fix permanente.

## Próximo paso

Track B (Deep Learning: LSTM, GRU, evaluación preliminar de TFT/híbrido
CNN-LSTM) — sin arrancar todavía. Ver la sección "Próximo paso (retomar
acá)" de `CLAUDE.md`, que es la fuente de estado autoritativa y se
mantiene actualizada en cada sesión — estas notas son un complemento
narrativo, no la reemplazan.
