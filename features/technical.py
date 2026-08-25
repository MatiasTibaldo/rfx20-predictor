"""
Technical indicators for OHLCV series.

Computes moving averages, RSI, MACD, and Bollinger Bands on a ``close``
column. The ``ta`` library operates on pandas Series, so conversion happens
locally per indicator call; the module's public interface stays Polars-in,
Polars-out (see CLAUDE.md convention: convert to pandas only where a
library requires it).
"""

from __future__ import annotations

import polars as pl
import ta
from loguru import logger

_DEFAULT_MA_WINDOWS = [10, 20, 50]
_RSI_WINDOW = 14


def add_technical_indicators(
    df: pl.DataFrame,
    ma_windows: list[int] | None = None,
) -> pl.DataFrame:
    """Append technical indicator columns computed from ``close``.

    The DataFrame is sorted by date before computing indicators. Columns
    added:

    - ``ma_{w}`` for each w in ma_windows: simple moving average of close.
    - ``rsi_14``: Relative Strength Index (Wilder, 14-period).
    - ``macd``, ``macd_signal``, ``macd_diff``: MACD with library defaults
      (12/26/9 EMA windows).
    - ``bb_high``, ``bb_low``, ``bb_mid``: Bollinger Bands with library
      defaults (20-period SMA, 2 standard deviations).

    Args:
        df: DataFrame with ``date`` (Date) and ``close`` (Float64) columns.
        ma_windows: Moving-average window sizes in trading days.
            Defaults to [10, 20, 50].

    Returns:
        DataFrame with appended indicator columns. Each indicator carries
        the usual rolling warm-up nulls at the start of the series.
    """
    if ma_windows is None:
        ma_windows = _DEFAULT_MA_WINDOWS

    df = df.sort("date")
    close_pd = df["close"].to_pandas()

    ma_columns = [
        pl.Series(f"ma_{w}", ta.trend.sma_indicator(close_pd, window=w).to_numpy())
        for w in ma_windows
    ]

    rsi = pl.Series("rsi_14", ta.momentum.rsi(close_pd, window=_RSI_WINDOW).to_numpy())

    macd_calc = ta.trend.MACD(close_pd)
    macd_columns = [
        pl.Series("macd", macd_calc.macd().to_numpy()),
        pl.Series("macd_signal", macd_calc.macd_signal().to_numpy()),
        pl.Series("macd_diff", macd_calc.macd_diff().to_numpy()),
    ]

    bb_calc = ta.volatility.BollingerBands(close_pd)
    bb_columns = [
        pl.Series("bb_high", bb_calc.bollinger_hband().to_numpy()),
        pl.Series("bb_low", bb_calc.bollinger_lband().to_numpy()),
        pl.Series("bb_mid", bb_calc.bollinger_mavg().to_numpy()),
    ]

    df = df.with_columns(*ma_columns, rsi, *macd_columns, *bb_columns)

    logger.debug(
        f"[technical] Added MA{ma_windows}, RSI({_RSI_WINDOW}), MACD, "
        f"Bollinger Bands ({len(df):,} rows)."
    )
    return df


def add_technical_indicators_all(
    dfs: dict[str, pl.DataFrame],
    ma_windows: list[int] | None = None,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`add_technical_indicators` to every ticker in a dict.

    Args:
        dfs: Mapping of ticker → OHLCV DataFrame.
        ma_windows: Moving-average window sizes forwarded to
            :func:`add_technical_indicators`.

    Returns:
        New dict with the same keys and DataFrames augmented with
        indicator columns.
    """
    results = {
        ticker: add_technical_indicators(df, ma_windows) for ticker, df in dfs.items()
    }
    logger.info(f"[technical] add_technical_indicators_all done: {len(results)} tickers.")
    return results
