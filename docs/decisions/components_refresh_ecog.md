# Decisión: actualización de los 27→28 componentes hasta hoy (26 ago 2026)

**Fecha:** 26 de agosto de 2026
**Módulos:** `ingestion/instruments.py`, `data/raw/v1/*_ohlcv.parquet`

## Contexto

Tras extender índice + macro hasta 2026-08-25 (Etapa 4), quedó pendiente
si los 27 componentes también debían actualizarse. No era necesario para
`features_long.parquet` (Opción A no los usa), pero sí para no dejar
`technical_components_long.parquet` desactualizado — y para sumar **ECOG**,
que entró a la composición del índice ~2026-05-04
(ver `docs/decisions/rfx20_ws_backfill.md`) y nunca estuvo en
`ingestion/instruments.py::RFX20_TICKERS`.

## Qué se hizo

1. Se agregó `ECOG` a `RFX20_TICKERS` (28 tickers). Se confirmó que
   resuelve con la misma convención de la API de Primary S.A.
   (`bm_MERV_ECOG_24hs`) antes de correr todo.
2. **Hallazgo de diseño:** `IngestionPipeline._process_ticker()` saltea el
   fetch si el parquet ya existe en disco (`store.parquet_exists`) — es un
   checkpoint para reanudar después de una falla parcial, no un mecanismo
   de refresh incremental. Correr `pipeline_runner` sin más solo hubiera
   traído ECOG (nuevo) y dejado los otros 27 tickers intactos en su fecha
   vieja (~mayo 2026). Se resolvió borrando los 27 parquets existentes en
   `data/raw/v1/*_ohlcv.parquet` antes de re-correr — fuerza una
   redescarga completa para todos, que es el comportamiento esperado del
   checkpoint (no es un workaround por fuera del diseño).
3. Re-corridos en secuencia: `ingestion.pipeline_runner` (Nodo 2, 28
   tickers hasta hoy) → `processing.runner` (Nodo 3) →
   `features.runner` (Nodo 4).

## Resultado

- `technical_components_long.parquet`: 28 tickers, 53.789 filas,
  2018-01-02 → 2026-08-25.
- ECOG: 388 filas, 2025-01-21 → 2026-08-25 (la API tiene historial desde
  antes de que ECOG entrara al índice — no hay problema, `in_index` sigue
  marcando correctamente el período de membresía real, misma filosofía
  que el resto de los componentes).
- `features_long.parquet` (Opción A) no cambió de contenido — sigue sin
  usar componentes — pero ahora todo el proyecto está en un mismo
  horizonte temporal (2026-08-25/26) de punta a punta.
