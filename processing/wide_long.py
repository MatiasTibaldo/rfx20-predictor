"""
Wide and long format dataset builders for the processed OHLCV layer.

Converts a dict of per-ticker DataFrames into the two canonical storage
formats and persists them via DuckDBStore.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger

from storage.store import DuckDBStore


def build_long(dfs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Stack all ticker DataFrames vertically into a long-format dataset.

    Each input DataFrame must already carry a ``ticker`` column (present in
    raw OHLCV files). Rows are sorted by ``date`` then ``ticker``.

    Args:
        dfs: Mapping of ticker → processed OHLCV DataFrame.

    Returns:
        Single long-format DataFrame with all tickers stacked.
        Returns an empty DataFrame if ``dfs`` is empty.
    """
    frames = list(dfs.values())
    if not frames:
        return pl.DataFrame()

    result = pl.concat(frames, how="diagonal").sort(["date", "ticker"])
    logger.debug(
        f"[wide_long] build_long: {len(result):,} rows from {len(dfs)} tickers."
    )
    return result


def build_wide(dfs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Pivot all ticker DataFrames into a wide-format dataset.

    Non-date, non-ticker columns are renamed as ``{TICKER}_{col}``. All frames
    are joined on ``date`` using a full outer join so no trading day is lost.

    Args:
        dfs: Mapping of ticker → processed OHLCV DataFrame.

    Returns:
        Wide-format DataFrame indexed by ``date``.
        Returns an empty DataFrame if ``dfs`` is empty.
    """
    if not dfs:
        return pl.DataFrame()

    _EXCLUDE = {"date", "ticker"}
    frames = []
    for ticker, df in dfs.items():
        prefix = ticker.upper()
        renamed = (
            df.drop([c for c in df.columns if c in _EXCLUDE and c != "date"])
            .rename({c: f"{prefix}_{c}" for c in df.columns if c not in _EXCLUDE})
        )
        frames.append(renamed)

    result = frames[0]
    for frame in frames[1:]:
        result = result.join(frame, on="date", how="full", coalesce=True)

    result = result.sort("date")
    logger.debug(
        f"[wide_long] build_wide: {len(result):,} rows, "
        f"{len(result.columns)} columns."
    )
    return result


def save_datasets(
    dfs: dict[str, pl.DataFrame],
    store: DuckDBStore,
    version: str = "v1",
) -> tuple[Path, Path]:
    """Build and persist long and wide datasets via DuckDBStore.

    Args:
        dfs: Mapping of ticker → processed OHLCV DataFrame.
        store: DuckDBStore instance for Parquet I/O.
        version: Version tag for the output files.

    Returns:
        Tuple of (long_path, wide_path).
    """
    long_df = build_long(dfs)
    wide_df = build_wide(dfs)

    long_path = store.save_parquet(
        long_df, layer="processed", name="ohlcv_long", version=version
    )
    wide_path = store.save_parquet(
        wide_df, layer="processed", name="ohlcv_wide", version=version
    )

    logger.info(
        f"[wide_long] Saved long ({len(long_df):,} rows) and "
        f"wide ({len(wide_df):,} rows, {len(wide_df.columns)} cols)."
    )
    return long_path, wide_path
