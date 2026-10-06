# Bug: doble ajuste de splits en Nodo 3 para BYMA (y casi YPFD/MIRG)

**Fecha:** 16 de septiembre de 2026
**Módulos afectados:** `config/data_corrections.yaml`, `processing/pipeline.py`
**Severidad:** medio-alto para BYMA (dato procesado objetivamente mal desde
que se agregó su primer split); evitado a tiempo para YPFD/MIRG.

## Contexto

Al investigar `docs/decisions/desvios_cronicos_composicion_vs_ohlcv.md` se
agregaron entradas de split para YPFD y MIRG en
`config/data_corrections.yaml::splits` — la misma sección donde ya vivían
los 3 splits de BYMA. Antes de dar por cerrado ese trabajo se verificó si
`fig_weight_history` (el consumidor que motivó el hallazgo) necesitaba
algún cambio de código, y en esa verificación apareció este bug.

## El error

`splits:` tiene un único consumidor en código:
`processing/pipeline.py` (Nodo 3), que llama
`SplitAdjuster.adjust_all(dfs, enforce_index_only=...)` sobre el OHLCV
**crudo** de cada ticker, aplicando un ajuste hacia atrás (factor `1/ratio`
para fechas anteriores al split). Esa lógica asume que el OHLCV crudo del
ticker es **nominal** (sin ajustar) — cierto para COME/AGRO/MORI, cuyos
splits son reales desdoblamientos no reflejados en el feed de Primary S.A.
(confirmado: el raw de COME muestra un salto real de precio exactamente en
la fecha de su split, 3,16 → 1,91 el 2019-08-02/06).

Pero BYMA, YPFD y MIRG son un caso distinto: su OHLCV crudo **ya viene
retroajustado** por el feed en vivo (Matriz) — no hay salto visible en la
fecha del split porque el feed, al refrescarse, reescribe toda la serie
histórica como si el split ya hubiera pasado siempre. Aplicarles el mismo
ajuste hacia atrás de `SplitAdjuster` es ajustar algo que ya está ajustado
— un **doble ajuste**.

## Evidencia

`data/raw/v1/byma_ohlcv.parquet`, 2020-01-15: `close = 2,91` (ya
retroajustado por los 3 splits futuros de BYMA). Pero
`data/processed/v1/ohlcv_long.parquet` (salida de Nodo 3, con los 2
splits de BYMA que ya estaban documentados antes de esta sesión: 10:1 en
2022, 5:1 en 2024) tenía `close = 0,0582` para la misma fila — exactamente
`2,91 / 50` (10×5, el factor acumulado de esos dos splits aplicado por
segunda vez). Este error es **anterior a esta sesión** — viene desde que
se agregó el primer split de BYMA a la configuración, no fue introducido
hoy. Lo que sí hubiera pasado hoy, si no se detectaba, es que YPFD y MIRG
recibieran el mismo trato al agregarles entradas en `splits:`.

## Decisión

Separar en dos secciones según a qué consume cada una:

- **`splits:`** — solo tickers cuyo OHLCV crudo es nominal y necesita el
  ajuste hacia atrás de `SplitAdjuster`/Nodo 3 (COME, AGRO, MORI).
- **`composition_only_splits:`** (nueva) — tickers cuyo OHLCV crudo ya
  viene ajustado por el feed (BYMA, YPFD, MIRG). Documentan el mismo tipo
  de evento (ratio, fecha, in_index) pero **no** los toca
  `SplitAdjuster.adjust_series`/`adjust_all` — quedan disponibles
  únicamente para el reescalado de composición pendiente (ver
  `docs/decisions/desvios_cronicos_composicion_vs_ohlcv.md`).

No hay forma de distinguir estos dos casos automáticamente desde el CSV
crudo — depende de qué feed/convención use cada proveedor del dato.
**Regla para el futuro:** antes de agregar un ticker nuevo a `splits:`,
verificar que su OHLCV crudo muestre un salto real de precio en la fecha
del split (como se hizo para COME); si el precio ya es continuo alrededor
del split (como BYMA/YPFD/MIRG), va en `composition_only_splits:`, nunca
en `splits:`.

## Corrección y verificación

1. Movidas las 5 entradas (BYMA×3, MIRG, YPFD) de `splits:` a
   `composition_only_splits:` en `config/data_corrections.yaml`.
2. `SplitAdjuster().get_splits_for_ticker("BYMA"/"YPFD"/"MIRG")` → `[]`
   confirmado (antes devolvía las entradas y las aplicaba).
3. Re-corrido Nodo 3 (`uv run python -m processing.runner`): BYMA en
   `ohlcv_long.parquet` vuelve a coincidir con el crudo (2,91, antes
   0,0582), `split_adjusted=false`. COME sigue ajustado correctamente
   (`split_adjusted=true`, valor consistente con su cadena de splits
   reales).
4. Re-corrido Nodo 4 (`uv run python -m features.runner`) para
   regenerar `technical_components_long.parquet` con el OHLCV corregido.

## Impacto en Bloque 2 (modelos)

**Ninguno.** `features_long.parquet` (el único dataset que consumen los 10
modelos de Bloque 2) se construye desde `rfx20_spot.parquet` + macro —
nunca desde `ohlcv_long.parquet`/`technical_components_long.parquet` (los
27 componentes individuales quedan deliberadamente fuera, ver
`docs/decisions/temporal_split_and_consolidation.md`, Opción A). Verificado
explícitamente: `features_long.parquet` resultante de la re-corrida de
Nodo 4 es idéntico al de antes de este fix (mismo `log_return` para
2019-09-23, mismo máximo absoluto de la serie). Las conclusiones de
Bloque 2 (incluida la reversión de GARCH, `track_a_b_sintesis_direccion_volatilidad.md`)
no cambian — este bug vivía en una capa de datos (OHLCV por componente)
que esos modelos nunca leen. Sí afecta a cualquier análisis que use
`technical_components_long.parquet` o `ohlcv_long/wide.parquet`
directamente (ninguno existe todavía en Bloque 2/3, pero queda disponible
para etapas futuras).
