"""
Index membership filter for OHLCV series.

Adds a boolean ``in_index`` column to each OHLCV DataFrame indicating whether
the ticker was a constituent of the RFX20 on each trading day.
"""

from __future__ import annotations

import polars as pl
from loguru import logger


def add_index_membership(
    ohlcv: pl.DataFrame,
    composition: pl.DataFrame,
    ticker: str,
) -> pl.DataFrame:
    """Add a boolean ``in_index`` column via left join on index composition dates.

    Checks each date in the OHLCV series against the dates on which the
    ticker appears in the composition DataFrame.

    Args:
        ohlcv: OHLCV DataFrame with a ``date`` column (pl.Date).
        composition: Index composition DataFrame with columns
            ``date`` (pl.Date) and ``ticker`` (str).
        ticker: Instrument symbol (case-insensitive).

    Returns:
        Copy of ``ohlcv`` with an appended ``in_index`` (Boolean) column.
    """
    ticker_upper = ticker.upper()
    composition_dates = (
        composition.filter(pl.col("ticker") == ticker_upper)
        .select("date")
        .unique()
    )

    result = ohlcv.with_columns(
        pl.col("date").is_in(composition_dates["date"]).alias("in_index")
    )

    in_count = result["in_index"].sum()
    total = len(result)
    logger.debug(f"[filter] {ticker_upper}: {in_count}/{total} days in index.")
    return result


def add_index_membership_all(
    dfs: dict[str, pl.DataFrame],
    composition: pl.DataFrame,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`add_index_membership` to every ticker in a dict.

    Args:
        dfs: Mapping of ticker → OHLCV DataFrame.
        composition: Full index composition DataFrame.

    Returns:
        New dict with the same keys and DataFrames augmented with ``in_index``.
    """
    results: dict[str, pl.DataFrame] = {
        ticker: add_index_membership(df, composition, ticker)
        for ticker, df in dfs.items()
    }
    logger.info(f"[filter] add_index_membership_all done: {len(results)} tickers.")
    return results
