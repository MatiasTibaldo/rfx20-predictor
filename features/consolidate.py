"""
Consolidación final de Nodo 4: une índice + macro + split temporal en
``features_long.parquet`` (Opción A — ver docs/decisions/temporal_split.md).

Deliberadamente NO incluye los 27 componentes pivotados a wide: no hay
consumidor concreto todavía que los necesite en esta forma, y
``technical_components_long.parquet`` sigue disponible aparte para
cualquier modelo que quiera estructura por ticker (misma lógica de "wide +
long persistidos, cada modelo elige" ya usada en Nodo 3).
"""

from __future__ import annotations

from datetime import date

import polars as pl
from loguru import logger

from .temporal_split import add_temporal_split

# Primera fecha de datos genuinamente out-of-sample (traídos del WS de
# MatbaRofex el 26-ago-2026, nunca antes disponibles en el proyecto — ver
# docs/decisions/rfx20_ws_backfill.md). Fijo, no se recalcula en cada
# corrida: si se agregan más datos históricos más adelante, este corte NO
# debe correrse solo porque el pipeline se re-ejecuta.
DEFAULT_TEST_START = date(2026, 4, 20)
DEFAULT_TRAIN_RATIO = 0.85
DEFAULT_VAL_RATIO = 0.15


def build_features_long(
    index_df: pl.DataFrame,
    macro_df: pl.DataFrame,
    test_start: date | None = DEFAULT_TEST_START,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    val_ratio: float = DEFAULT_VAL_RATIO,
) -> pl.DataFrame:
    """Join index-level features + macro features + temporal split.

    Both inputs are already aligned to the same daily calendar (see
    ``features/pipeline.py`` — ``macro_df`` is built via
    ``join_asof`` against ``index_df["date"]``), so a plain join on
    ``date`` is enough here — no asof needed at this step.

    Args:
        index_df: Output of Etapa 1 (technical indicators + volatility +
            target on the RFX20 index itself).
        macro_df: Output of Etapa 2 (spreads, tasas, IPC, futuros).
        test_start: Forwarded to :func:`features.temporal_split.add_temporal_split`.
        train_ratio: Forwarded (renormalized against ``val_ratio`` when
            ``test_start`` is set).
        val_ratio: Forwarded.

    Returns:
        DataFrame with one row per trading day, all index + macro feature
        columns, and a ``split`` column (``"train"``/``"val"``/``"test"``).
    """
    result = index_df.join(macro_df, on="date", how="inner")
    if result.height != index_df.height:
        logger.warning(
            f"[consolidate] join índice+macro perdió filas: "
            f"{index_df.height:,} → {result.height:,}. Revisar calendarios."
        )

    split_df = add_temporal_split(
        result["date"], test_start=test_start, train_ratio=train_ratio, val_ratio=val_ratio
    )
    result = result.join(split_df, on="date", how="left")

    logger.info(
        f"[consolidate] features_long: {result.height:,} filas, "
        f"{len(result.columns)} columnas."
    )
    return result
