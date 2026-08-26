# Decisión: backfill de datos RFX20 vía WS de MatbaRofex (25-26 ago 2026)

**Fecha:** 26 de agosto de 2026
**Módulos:** `ingestion/rfx20_index.py`, `ingestion/rfx20_composition_ws.py`,
`scripts/update_rfx20_spot.py`, `scripts/backfill_rfx20_composition.py`

## Contexto

Al definir el particionamiento temporal (Nodo 4, Etapa 4) surgió la
posibilidad de usar datos genuinamente nuevos (nunca vistos) como test set,
en vez de recortar del historial existente. El spot del RFX20 solo llegaba
hasta 2026-04-17; el alumno proveyó una conexión WS de MatbaRofex
(`ws.matbarofex.com.ar:8999`) con cuatro endpoints:

- `GET /api/rfx20/index?from=X&to=Y` — spot oficial diario, con rango de
  fechas (un solo request cubre meses).
- `GET /api/rfx20/historical?date=X` — composición + precio por
  instrumento, una fecha por request.
- `GET /api/rfx20/divisor?date=X` — divisor vigente, una fecha por request.
- `GET /api/rfx20` — snapshot "actual": cartera vigente + proyectada +
  histórica de la fecha más reciente disponible.

## Nota TLS

El certificado de `ws.matbarofex.com.ar` tiene la cadena incompleta (falta
el intermedio) — la verificación estándar falla incluso con `curl` sin
flags. Se deshabilitó verificación TLS (`verify=False`) explícitamente en
los tres conectores nuevos, documentado en el código y acá. Es un endpoint
provisto directamente por el alumno (infraestructura de Primary S.A./
MatbaRofex), no una fuente de terceros no confiable — pero sigue siendo una
decisión de seguridad que vale la pena tener registrada.

## Qué se trajo

- **Spot** (`historico_spot_rfx20.csv`): 86 filas nuevas, 2026-04-20 →
  2026-08-25. Solo se agregaron fechas nuevas — ningún valor histórico
  existente se tocó (`scripts/update_rfx20_spot.py`).
- **Cartera Historica**: 86 archivos nuevos (`cartera_historica_YYYYMMDD.csv`),
  uno por rueda, mismo esquema que los ~1900 archivos existentes.
- **Divisor** (`divisores.csv`): 12 filas nuevas — solo se agregó una fila
  cuando el valor cambió respecto a la fila anterior (mismo patrón disperso
  del archivo original, no una fila por día).
- **Cartera Vigente / Proyectada**: primero se agregó un solo snapshot de
  cada una desde `/api/rfx20` (`nvas_cantidades_20260812.csv`,
  `proyectada_20260820.csv`) — pero eso dejó un hueco: entre el 15-abr
  (última Vigente pre-backfill) y el 12-ago no había ningún archivo
  intermedio, pese a que la composición sí cambió en el medio (el alumno
  detectó esto y preguntó explícitamente). Se corrigió con
  `scripts/backfill_vigente_changepoints.py`: en vez de pegarle de nuevo a
  la API, se derivaron los puntos de cambio real comparando la composición
  día a día en Cartera Historica (ya completa) contra el día anterior — 12
  cambios detectados, 11 archivos nuevos de Cartera Vigente escritos ahí
  (el del 12-ago ya existía). Cartera Proyectada **no** se pudo backfillear
  de la misma forma — es una proyección anunciada hacia adelante en un
  momento dado, no reconstruible desde el historial de composición
  efectiva; sigue con un solo snapshot.

Después del backfill se corrió `ingestion.composition_runner` para
regenerar `data/raw/v1/*.parquet`, y `features.runner` para extender
`technical_index.parquet` y `macro.parquet` (ahora 2041 filas,
2018-04-03 → 2026-08-25).

## Hallazgo: nuevo componente del índice (ECOG)

La composición vigente al 25/08/2026 incluye **ECOG**, que no estaba en
`ingestion/instruments.py::RFX20_TICKERS` (27 tickers). Entró al índice
alrededor del 2026-05-04. **No se agregó su ingesta de OHLCV** — está fuera
de alcance para esta etapa (que usa Opción A: índice + macro, sin
componentes en `features_long.parquet`). Si en el futuro se necesitan los
27+ componentes actualizados (Opción B, o Bloque 2), hay que sumar ECOG a
`RFX20_TICKERS` y correr `ingestion.pipeline_runner` antes de asumir que la
lista de 27 sigue completa.

## "Solo por esta vez"

El alumno pidió explícitamente que este backfill se documentara como algo
puntual, no un patrón a repetir automáticamente en cada corrida del
pipeline — `scripts/update_rfx20_spot.py` y
`scripts/backfill_rfx20_composition.py` son scripts manuales (mismo patrón
que `fetch_rfx20_futures.py`), no nodos del pipeline de Streamlit.
