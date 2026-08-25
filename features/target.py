"""
Target variable construction for the RFX20 index itself.

Unlike the per-component return columns already present in
``ohlcv_long.parquet``, the index-level log return is not computed anywhere
upstream — ``rfx20_spot.parquet`` only carries the raw daily index value.
This module builds it from the official spot series, reusing the same
return formula as the per-component pipeline (``processing.returns``)
instead of duplicating it.
"""

from __future__ import annotations

import polars as pl
from loguru import logger

from processing.returns import add_returns


def build_index_target(
    spot_df: pl.DataFrame,
    horizons: list[int] | None = None,
) -> pl.DataFrame:
    """Compute log/simple returns and forward returns for the RFX20 index.

    Args:
        spot_df: RFX20 spot DataFrame with ``date`` (Date) and ``value``
            (Float64) columns, as loaded from ``raw/rfx20_spot``.
        horizons: Prediction horizons in business days. Defaults to [1, 3, 5]
            (``processing.returns.add_returns`` default).

    Returns:
        DataFrame with columns ``date``, ``close`` (renamed from ``value``),
        ``log_return``, ``simple_return``, and ``log_return_fwd_{h}`` for
        each h in horizons.
    """
    df = spot_df.rename({"value": "close"})
    df = add_returns(df, horizons)

    logger.info(
        f"[target] build_index_target done: {len(df):,} rows, "
        f"horizons={horizons or [1, 3, 5]}."
    )
    return df
