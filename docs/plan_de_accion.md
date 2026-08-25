# Plan de acción — hacia la presentación (objetivo: antes de diciembre 2026)

**Fecha de elaboración:** 20 de agosto de 2026
**Contexto:** replanificación tras 7 semanas sin avance registrado (último commit de
procesamiento: 2026-07-02). El Plan de Trabajo Final preveía Fase 1 (8 sem) + Fase 2
(4 sem) = 12 semanas hasta cerrar features; llevamos ~20 semanas desde el inicio del
repositorio (2026-04-06) y Nodo 4 (features) todavía no arrancó.

## Diagnóstico

**Completado (~90% de la Fase 1 del plan original):**

- Nodo 1 — Composición histórica (27 tickers, 2018→hoy)
- Nodo 2 — Ingesta OHLCV de los 27 componentes
- Ajuste por splits (`processing/adjustments.py` + `config/splits.yaml`)
- Nodo 3 — `processing/` completo: filtro `in_index`, corrección de datos sucios,
  retornos log, dummies macro, datasets wide/long, reconstrucción del índice
- Datos macro consolidados en `data/raw/macro/` (dólares, riesgo país, tasa PF, IPC, Merval)

**Sin iniciar:** Nodo 4 (`features/`) — solo existe el `__init__.py`.
`pipeline_state.json` marca `features: running`, pero es un estado de runner sin
código de features real detrás.

**Brecha de cronograma:** las fases pendientes (Features 4 + ML/Estadísticos 6 + DL 6 +
Selección 3 + Documentación 10 = 29 semanas en secuencial) no entran en las ~14 semanas
disponibles hasta fin de noviembre. Estrategia acordada: **no recortar alcance, no mover
la fecha objetivo** → correr Fase 3 y Fase 4 en paralelo (tal como el propio plan de
trabajo lo habilita) y mover la redacción de la tesis de "bloque final" a "hilo continuo"
desde ahora, con devoluciones periódicas de los directores.

Este es un plan **sin holgura**. El mayor riesgo es el track de Deep Learning
(sin GPU). Si se atrasa, el amortiguador es reducir profundidad en lo que el propio
plan ya trata como preliminar/exploratorio (evaluación de TFT, arquitectura híbrida
CNN-LSTM) — no en los entregables duros (ARIMA/SARIMA, GARCH, SVM/RF/XGBoost/LightGBM,
LSTM/GRU, selección final).

## Estado de las decisiones bloqueantes del Bloque 1 (actualizado 20 ago 2026)

- **Librería de indicadores técnicos → resuelto: `ta`.** Se descartó `pandas-ta`
  al intentar instalarlo (requiere Python >=3.12; el proyecto está fijado en
  3.11) y `ta-lib` por requerir compilación nativa. Instalado con `uv add ta`.
- **Tracking de experimentos → resuelto: se suma MLflow.** El alumno ya lo usó
  antes y, dado el volumen de corridas que vienen en el Bloque 2 (múltiples
  familias de modelos, grid/random search con CV temporal, en dos tracks
  paralelos), tiene más sentido que reconstruir un esquema a mano en DuckDB.
  Instalado con `uv add mlflow`, backend local (`mlruns/`, sin server).
  `results/experiments.duckdb` sigue a cargo del estado del pipeline y los datos;
  MLflow trackea específicamente las corridas de modelos desde Fase 3.
- **Lag de publicación del IPC → resuelto con precisión para dic-2023 a may-2026**
  (fechas exactas de los calendarios de difusión de INDEC) y aproximación
  documentada (+12 días corridos) para 2018 a nov-2023. Ver
  `docs/decisions/ipc_publication_lag.md`.
- **Excel de dividendos en especie → resuelto: no se persigue.** Impacto en
  precio inmaterial. Ver `docs/decisions/dividends_and_splits.md` sección 4.
- **BADLAR/TAMAR → resuelto (25 ago 2026).** El alumno sumó `badlar.csv`/`tamar.csv`
  manualmente a `data/raw/macro/`. Validados (sin nulls/duplicados) e incorporados en
  Etapa 2 de Nodo 4. Ver `docs/decisions/macro_features_etapa2.md`.
- **Volatilidad implícita (futuros RFX20) → resuelto con cambio de alcance e
  implementado (24-25 ago 2026).** URL de la API de MatbaRofex provista. RFX20 no
  tiene mercado de opciones con volumen, por lo que no hay IV real que calcular;
  se reinterpreta como tasa implícita (`impliedRate`) + term spread de la
  curva de futuros. Ver `docs/decisions/futures_implied_rate.md`.

## Cronograma (14 semanas, 20 ago → 30 nov)

| Bloque | Fechas | Semanas | Contenido |
|---|---|---|---|
| 1. Features (Nodo 4) | 20 ago – 10 sep | 3 | Fase 2 completa |
| 2. Modelos en paralelo | 11 sep – 29 oct | 7 | Fase 3 (estadísticos + ML) y Fase 4 (DL) simultáneas |
| 3. Comparación y selección | 30 oct – 12 nov | 2 | Fase 5: evaluación multicriterio, ensemble, modelo óptimo |
| 4. Cierre y consolidación | 13 nov – 28 nov | 2 | Fase 6: consolidar lo ya escrito, incorporar devoluciones, revisión final |

Deja 2-3 días de colchón antes del 1 de diciembre.

### Bloque 1 — Features (20 ago – 10 sep)

**Nota de ejecución (24 ago 2026):** el bloque se construye **por etapas**
(no de una sola vez), para validar cada dataset de features antes de sumar
el siguiente. Progreso:

- **Etapa 1 (tareas 1-2, completa 24 ago 2026):** indicadores técnicos +
  volatilidad realizada, sobre los 27 componentes y sobre el propio índice
  RFX20, más la construcción del target del índice (no existía antes). Ver
  `docs/decisions/technical_indicators_scope.md`. Código en `features/`
  (`technical.py`, `volatility.py`, `target.py`, `pipeline.py`, `runner.py`).
  Output intermedio: `data/features/v1/technical_components_long.parquet` y
  `technical_index.parquet`.
- **Etapa 2 (tarea 3, completa 25 ago 2026):** features macro — spreads
  cambiarios (oficial/informal/mep/ccl), riesgo país, tasa PF, BADLAR,
  TAMAR, IPC con lag de publicación, tasa implícita + term spread de
  futuros RFX20. Ver `docs/decisions/macro_features_etapa2.md`. Código
  nuevo: `ingestion/futures.py`, `scripts/fetch_rfx20_futures.py`,
  `features/macro.py`. Output intermedio: `data/features/v1/macro.parquet`.
- **Etapa 3 (tarea 4, completa 25 ago 2026):** exploración de
  diferenciación fraccional (FFD, López de Prado, a mano). d=0.35 mínimo
  estacionario, correlación 0.56 vs. 0.03 del log-return completo. No se
  productiviza — queda para Track A de Bloque 2 si hace falta. Ver
  `docs/decisions/fractional_differentiation.md`. Script:
  `scripts/fractional_diff_exploration.py`.
- **Etapa siguiente (pendiente):** particionamiento temporal +
  consolidación en `features_long.parquet` (tarea 5) — cierra Bloque 1.

**Decisiones ya resueltas** (detalle en la sección anterior y en `CLAUDE.md`):
librería de indicadores técnicos (`ta`), tracking de experimentos (MLflow + DuckDB),
lag de publicación del IPC, dividendos en especie, URL y tasa implícita de futuros
RFX20, BADLAR/TAMAR.

**Sigue pendiente:** particionamiento temporal 70/15/15 (tarea 5).

**Tareas técnicas:**

1. ~~Indicadores técnicos: MA(10,20,50), RSI(14), MACD, Bandas de Bollinger~~ — Etapa 1, completa
2. ~~Volatilidad realizada (rolling std de `log_return`)~~ — Etapa 1, completa
3. ~~Features macro transformados: term spread, spreads cambiarios múltiples, tasa implícita de futuros~~ — Etapa 2, completa
4. ~~Diferenciación fraccional — exploración acotada, no bloqueante~~ — Etapa 3, completa
5. Particionamiento temporal 70/15/15 + `features_long.parquet`

### Bloque 2 — Modelos en paralelo (11 sep – 29 oct)

- **Track A (estadístico + ML clásico):** ARIMA/SARIMA + GARCH primero (baseline
  rápido) → SVM, Random Forest, XGBoost, LightGBM con validación cruzada temporal.
- **Track B (Deep Learning):** ventanas/lookback → LSTM y GRU → evaluación preliminar
  de TFT/Transformer → híbrido CNN-LSTM. Entrenamientos largos corren de fondo
  (overnight) sin bloquear el resto del trabajo.
- Checkpoint semanal (viernes): estado de ambos tracks + avance de redacción. Si un
  track se atrasa más de una semana, se decide ahí mismo qué profundidad exploratoria
  se recorta, sin tocar el checkpoint 4 de directores.

### Bloque 3 — Comparación y selección (30 oct – 12 nov)

- Framework de evaluación multicriterio (RMSE/MAE/MAPE, hit ratio, backtesting con
  Sharpe/drawdown, robustez por régimen de volatilidad)
- Ensemble (promedio/ponderado/stacking)
- Selección del modelo óptimo + feature importance final

### Bloque 4 — Cierre (13 nov – 28 nov)

- Consolidar lo redactado en los bloques 1-3 (no arrancar de cero)
- Incorporar devoluciones de los checkpoints anteriores
- Conclusiones, limitaciones, trabajo futuro
- Revisión final con Fernanda Mendez y Rodrigo Del Rosso — margen no comprimible

## Track paralelo: redacción y devoluciones de directores

| Checkpoint | Cuándo | Contenido enviado |
|---|---|---|
| 0 | 22-24 ago 2026 | Informe de avance: Nodos 1-3 + decisiones metodológicas documentadas |
| 1 | ~10 sep (cierre Bloque 1) | Sección Datos + Metodología de Features |
| 2 | ~10 oct (cierre Track A) | Resultados preliminares de modelos estadísticos/ML |
| 3 | ~12 nov (cierre Bloque 3) | Sección Resultados y comparación completa |
| 4 | ~28 nov | Documento completo para revisión final pre-presentación |

El checkpoint 0 usa contenido que ya existe (`docs/decisions/`, `CLAUDE.md`) — solo
requiere consolidarlo en formato de informe de avance.
