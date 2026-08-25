"""
Realized volatility for return series.

Rolling standard deviation of ``log_return`` over fixed windows, used as a
volatility feature alongside the technical indicators in ``technical.py``.
"""

from __future__ import annotations

import polars as pl
from loguru import logger

_DEFAULT_WINDOWS = [10, 20, 50]


def add_realized_volatility(
    df: pl.DataFrame,
    windows: list[int] | None = None,
) -> pl.DataFrame:
    """Append rolling realized-volatility columns computed from ``log_return``.

    Args:
        df: DataFrame with ``date`` (Date) and ``log_return`` (Float64) columns,
            already sorted or sortable by date.
        windows: Rolling window sizes in trading days. Defaults to [10, 20, 50]
            (matching the moving-average windows in ``technical.py``).

    Returns:
        DataFrame with appended ``realized_vol_{w}`` columns (rolling std of
        ``log_return``). Each column carries the usual rolling warm-up nulls
        at the start of the series.
    """
    if windows is None:
        windows = _DEFAULT_WINDOWS

    df = df.sort("date")
    df = df.with_columns(
        [
            pl.col("log_return").rolling_std(w).alias(f"realized_vol_{w}")
            for w in windows
        ]
    )

    logger.debug(f"[volatility] Added realized volatility for windows {windows}.")
    return df


def add_realized_volatility_all(
    dfs: dict[str, pl.DataFrame],
    windows: list[int] | None = None,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`add_realized_volatility` to every ticker in a dict.

    Args:
        dfs: Mapping of ticker → DataFrame with a ``log_return`` column.
        windows: Rolling window sizes forwarded to
            :func:`add_realized_volatility`.

    Returns:
        New dict with the same keys and DataFrames augmented with realized
        volatility columns.
    """
    results = {
        ticker: add_realized_volatility(df, windows) for ticker, df in dfs.items()
    }
    logger.info(
        f"[volatility] add_realized_volatility_all done: {len(results)} tickers."
    )
    return results
