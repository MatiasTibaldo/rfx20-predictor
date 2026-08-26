# Decisión: particionamiento temporal y consolidación en features_long.parquet

**Fecha:** 26 de agosto de 2026 (Nodo 4, Etapa 4 — cierra el Bloque 1)
**Módulos:** `features/temporal_split.py`, `features/consolidate.py`,
`features/pipeline.py` (Step 8)

## Contexto

Última tarea del Bloque 1: particionar train/val/test y consolidar en el
`features_long.parquet` final. El plan original preveía un split estático
70/15/15. Durante la discusión con el alumno surgieron dos objeciones que
cambiaron el diseño:

1. **Con un 70/15/15 sobre los datos históricos, el corte de train caía el
   16 de noviembre de 2023** — cinco días antes de las elecciones que este
   proyecto ya marca como evento macro relevante. El modelo nunca vería en
   entrenamiento el régimen post-electoral completo (devaluación dic-2023,
   toda la dinámica 2024-2026).
2. **Si ese tramo tiene información valiosa, se pierde para el
   entrenamiento** — válido, pero mitigado en la práctica porque el split
   solo sirve para *seleccionar* el modelo (Bloque 2-3); el modelo final se
   reentrena con el dataset completo antes de usarse.

La resolución fue mejor que solo ajustar proporciones: el alumno consiguió
datos genuinamente nuevos (nunca antes en el proyecto) vía WS de
MatbaRofex — ver `docs/decisions/rfx20_ws_backfill.md`. Eso permite un test
set 100% out-of-sample real, no un recorte del historial.

## Diseño final

- **Test = datos genuinamente nuevos**: `date >= 2026-04-20` (86 filas,
  hasta 2026-08-25). Nunca estuvieron en el proyecto antes de este backfill
  — cero posibilidad de que alguna decisión de feature engineering anterior
  se haya "asomado" a esas fechas.
- **Train/val = split cronológico 85/15 sobre el resto** (2018-04-03 →
  2026-04-17, 1955 filas): train hasta 2025-01-28 (1661 filas), val desde
  2025-01-29 (294 filas). Train ahora sí incluye todo el régimen
  post-electoral 2023-2025.
- **`test_start` es una fecha fija** (`DEFAULT_TEST_START = 2026-04-20` en
  `features/consolidate.py`), no calculada dinámicamente como "los últimos
  N% de lo que haya hoy". Si en el futuro se agregan más datos históricos y
  se vuelve a correr el pipeline, el corte de test **no debe correrse solo
  porque hay más filas** — es una decisión que se revisa a mano.

## Nota para Bloque 2-3 (a no perder de vista)

**El modelo final elegido debe reentrenarse con el dataset completo**
(train+val+test) antes de usarse para predicciones reales — el split
70/15/15-en-espíritu (acá 85/15+test-fijo) es una herramienta de selección
y evaluación honesta, no una exclusión permanente de esos datos del modelo
productivo. Sin este paso, el modelo final nunca vería el período más
reciente de los datos.

## `features_long.parquet` — Opción A (índice + macro, sin componentes)

Se optó por **no** pivotar los 27 componentes a wide y sumarlos acá.
Razones:

- Ningún modelo concreto necesita esa forma todavía — DL (LSTM) probablemente
  quiere estructura tiempo×ticker×features (tensor), no un tabla plana de
  ~800 columnas; ARIMA es univariado sobre el índice.
- `technical_components_long.parquet` (Etapa 1) sigue disponible aparte —
  misma filosofía "wide + long persistidos, cada modelo elige" que ya usa
  Nodo 3.
- Evita comprometerse a un esquema de ~800 columnas por adelantado sin un
  consumidor que lo justifique.

**Join:** `index_df` (Etapa 1) + `macro_df` (Etapa 2), `join` simple por
`date` — ambos ya comparten el mismo calendario (macro se construyó vía
`join_asof` contra las fechas del índice en Etapa 2), no hace falta asof acá.

## Salida

`data/features/v1/features_long.parquet` (+ csv hermano) — 2041 filas, 34
columnas: `date` + 19 columnas de índice (indicadores técnicos + target) +
13 de macro + `split`. Cierra el Bloque 1 del plan de acción.
