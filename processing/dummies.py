"""
Dummy variables for macro events.

Appends boolean and directional indicator columns based on macro events
loaded from config/splits.yaml.

"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger

from .adjustments import SplitAdjuster


def add_dummies(
    df: pl.DataFrame,
    config_path: Path | None = None,
) -> pl.DataFrame:
    """Append macro-event dummy columns to an OHLCV DataFrame.

    Columns added:
    - ``is_macro_event`` (Boolean): True on dates listed in ``macro_events``
      in splits.yaml.
    - ``macro_direction`` (Int8): +1 for positive events, -1 for negative,
      0 otherwise.

    Args:
        df: OHLCV DataFrame with a ``date`` (pl.Date) column.
        config_path: Path to splits.yaml. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        DataFrame with appended dummy columns.
    """
    adjuster = SplitAdjuster(config_path)
    macro_df = adjuster.get_macro_events()
    return _apply_dummies(df, macro_df)


def add_dummies_all(
    dfs: dict[str, pl.DataFrame],
    config_path: Path | None = None,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`add_dummies` to every ticker in a dict.

    Instantiates :class:`SplitAdjuster` once and reuses the macro-event
    DataFrame across all tickers.

    Args:
        dfs: Mapping of ticker -> OHLCV DataFrame.
        config_path: Path to splits.yaml. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        New dict with the same keys and DataFrames augmented with dummy columns.
    """
    adjuster = SplitAdjuster(config_path)
    macro_df = adjuster.get_macro_events()

    results = {ticker: _apply_dummies(df, macro_df) for ticker, df in dfs.items()}
    logger.info(f"[dummies] add_dummies_all done: {len(results)} tickers.")
    return results


def _apply_dummies(df: pl.DataFrame, macro_df: pl.DataFrame) -> pl.DataFrame:
    """Internal: add dummy columns given a pre-loaded macro events DataFrame."""
    if len(macro_df) == 0:
        return df.with_columns(
            pl.lit(False).alias("is_macro_event"),
            pl.lit(0).cast(pl.Int8).alias("macro_direction"),
        )

    macro_lookup = macro_df.with_columns(
        pl.when(pl.col("direction") == "positive")
        .then(pl.lit(1, dtype=pl.Int8))
        .when(pl.col("direction") == "negative")
        .then(pl.lit(-1, dtype=pl.Int8))
        .otherwise(pl.lit(0, dtype=pl.Int8))
        .alias("direction_code")
    ).select("date", "direction_code")

    return (
        df.join(macro_lookup, on="date", how="left")
        .with_columns(
            pl.col("direction_code").is_not_null().alias("is_macro_event"),
            pl.col("direction_code").fill_null(pl.lit(0, dtype=pl.Int8)).alias(
                "macro_direction"
            ),
        )
        .drop("direction_code")
    )
