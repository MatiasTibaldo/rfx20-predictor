"""
Log and simple return computation for OHLCV series.

Adds return columns to a DataFrame sorted by date, including forward
returns for each prediction horizon.
"""

from __future__ import annotations

import math

import polars as pl
from loguru import logger


def add_returns(
    df: pl.DataFrame,
    horizons: list[int] | None = None,
) -> pl.DataFrame:
    """Compute log and simple returns and append forward-return columns.

    The DataFrame is sorted by date before computing returns to guarantee
    temporal ordering. Columns added:

    - ``log_return``: ln(close_t / close_{t-1})
    - ``simple_return``: close_t / close_{t-1} - 1
    - ``log_return_fwd_{h}`` for each h in horizons: log_return shifted -h rows
      (i.e., the log return h periods into the future).

    Args:
        df: OHLCV DataFrame with ``date`` (Date) and ``close`` (Float64) columns.
        horizons: Prediction horizons in business days. Defaults to [1, 3, 5].

    Returns:
        DataFrame with appended return columns. The last h rows of each
        ``log_return_fwd_{h}`` column will be null (no future data available).
    """
    if horizons is None:
        horizons = [1, 3, 5]

    df = df.sort("date")

    df = df.with_columns(
        (pl.col("close").log(math.e) - pl.col("close").shift(1).log(math.e)).alias(
            "log_return"
        ),
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("simple_return"),
    )

    df = df.with_columns(
        [pl.col("log_return").shift(-h).alias(f"log_return_fwd_{h}") for h in horizons]
    )

    logger.debug(
        f"[returns] Added log_return, simple_return, "
        f"and forward returns for horizons {horizons}."
    )
    return df


def add_returns_all(
    dfs: dict[str, pl.DataFrame],
    horizons: list[int] | None = None,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`add_returns` to every ticker in a dict.

    Args:
        dfs: Mapping of ticker → OHLCV DataFrame.
        horizons: Prediction horizons forwarded to :func:`add_returns`.

    Returns:
        New dict with the same keys and DataFrames augmented with return columns.
    """
    if horizons is None:
        horizons = [1, 3, 5]

    results = {ticker: add_returns(df, horizons) for ticker, df in dfs.items()}
    logger.info(
        f"[returns] add_returns_all done: {len(results)} tickers, horizons={horizons}."
    )
    return results
