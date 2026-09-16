"""
Data cleaning: patches known dirty values in OHLCV series.

Reads the ``dirty_data`` section of config/splits.yaml and replaces
erroneous field values with the validated ``fix`` value for each entry.
Only entries that include a ``fix`` key are applied.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from loguru import logger

from config.settings import settings


def load_dirty_data(config_path: Path | None = None) -> pl.DataFrame:
    """Parse the ``dirty_data`` section of splits.yaml into a DataFrame.

    Only entries that carry a ``fix`` key are included — entries without
    a fix are documentation-only annotations.

    Args:
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        DataFrame with columns: ``ticker`` (String), ``date`` (Date),
        ``field`` (String), ``fix`` (Float64), ``notes`` (String).
        Returns an empty DataFrame with that schema if no actionable entries exist.
    """
    _EMPTY_SCHEMA = {
        "ticker": pl.String,
        "date": pl.Date,
        "field": pl.String,
        "fix": pl.Float64,
        "notes": pl.String,
    }

    path = config_path or settings.SPLITS_CONFIG
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    entries = [e for e in raw.get("dirty_data", []) if "fix" in e]
    if not entries:
        return pl.DataFrame(schema=_EMPTY_SCHEMA)

    rows = [
        {
            "ticker": str(e["ticker"]).upper(),
            "date": _to_date(e["date"]),
            "field": str(e.get("field", "")),
            "fix": float(e["fix"]),
            "notes": str(e.get("notes", "")),
        }
        for e in entries
    ]
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


def apply_corrections(
    df: pl.DataFrame,
    ticker: str,
    config_path: Path | None = None,
) -> pl.DataFrame:
    """Patch known dirty values for a single ticker.

    Reads entries from the ``dirty_data`` section of splits.yaml that have a
    ``fix`` value, and replaces the erroneous field value on the specified date.
    Appends a boolean ``data_patched`` column (True only on patched rows).

    Args:
        df: OHLCV DataFrame with a ``date`` column (pl.Date).
        ticker: Instrument symbol (case-insensitive).
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        DataFrame with patched values and a ``data_patched`` (Boolean) column.
    """
    ticker_upper = ticker.upper()
    dirty = load_dirty_data(config_path)
    ticker_dirty = dirty.filter(pl.col("ticker") == ticker_upper)

    if len(ticker_dirty) == 0:
        return df.with_columns(pl.lit(False).alias("data_patched"))

    result = df.with_columns(pl.lit(False).alias("data_patched"))
    for row in ticker_dirty.iter_rows(named=True):
        patch_date: datetime.date = row["date"]
        field: str = row["field"]
        fix: float = row["fix"]

        if field not in result.columns:
            logger.warning(
                f"[cleaner] {ticker_upper}: field {field!r} not in DataFrame — skip."
            )
            continue

        is_patch_row = pl.col("date").cast(pl.Date) == pl.lit(patch_date)
        result = result.with_columns(
            pl.when(is_patch_row)
            .then(pl.lit(fix))
            .otherwise(pl.col(field))
            .alias(field),
            pl.when(is_patch_row)
            .then(pl.lit(True))
            .otherwise(pl.col("data_patched"))
            .alias("data_patched"),
        )
        logger.info(
            f"[cleaner] {ticker_upper}: patched {field}={fix} on {patch_date}."
        )

    return result


def load_composition_price_corrections(config_path: Path | None = None) -> pl.DataFrame:
    """Parse the ``composition_price_corrections`` section of splits.yaml.

    See ``docs/decisions/sept2019_composicion_corrupta.md`` for the full
    investigation: the ``close`` embedded in ``rfx20_composition.parquet``
    (sourced from ``cartera_historica_*.csv``) is corrupted for a handful of
    tickers/dates — confirmed against MatbaRofex's own historical API, so the
    error is in the source, not in ingestion. ``quantity`` is unaffected.

    Args:
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        DataFrame with columns ``ticker`` (String), ``date`` (Date),
        ``fix`` (Float64). Empty (with that schema) if none are configured.
    """
    _EMPTY_SCHEMA = {"ticker": pl.String, "date": pl.Date, "fix": pl.Float64}

    path = config_path or settings.SPLITS_CONFIG
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    entries = raw.get("composition_price_corrections", [])
    if not entries:
        return pl.DataFrame(schema=_EMPTY_SCHEMA)

    rows = [
        {
            "ticker": str(e["ticker"]).upper(),
            "date": _to_date(e["date"]),
            "fix": float(e["fix"]),
        }
        for e in entries
    ]
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


def apply_composition_price_corrections(
    df: pl.DataFrame,
    config_path: Path | None = None,
) -> pl.DataFrame:
    """Patch corrupted ``close`` values in the long-format RFX20 composition frame.

    Unlike :func:`apply_corrections` (single-ticker OHLCV frames), this
    operates directly on the long-format ``rfx20_composition.parquet`` shape
    (``date``, ``ticker``, ``quantity``, ``close`` for all 20 constituents),
    matching on both ``ticker`` and ``date``. Kept separate from
    ``dirty_data`` so a composition-only fix (e.g. a rescaled BYMA/YPFD value,
    see the decision doc) can never leak into that ticker's own raw OHLCV
    series via :func:`apply_corrections`.

    Args:
        df: Long-format composition DataFrame with ``date``, ``ticker``,
            ``close`` columns.
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        DataFrame with ``close`` patched and an appended ``price_corrected``
        (Boolean) column.
    """
    corrections = load_composition_price_corrections(config_path)
    if corrections.height == 0:
        return df.with_columns(pl.lit(False).alias("price_corrected"))

    result = df.with_columns(pl.lit(False).alias("price_corrected"))
    for row in corrections.iter_rows(named=True):
        mask = (pl.col("ticker") == row["ticker"]) & (
            pl.col("date").cast(pl.Date) == pl.lit(row["date"])
        )
        result = result.with_columns(
            pl.when(mask).then(pl.lit(row["fix"])).otherwise(pl.col("close")).alias("close"),
            pl.when(mask).then(pl.lit(True)).otherwise(pl.col("price_corrected")).alias("price_corrected"),
        )

    n_patched = result["price_corrected"].sum()
    logger.info(f"[cleaner] apply_composition_price_corrections: {n_patched} row(s) patched.")
    return result


def apply_corrections_all(
    dfs: dict[str, pl.DataFrame],
    config_path: Path | None = None,
) -> dict[str, pl.DataFrame]:
    """Apply :func:`apply_corrections` to every ticker in a dict.

    Args:
        dfs: Mapping of ticker → OHLCV DataFrame.
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Returns:
        New dict with the same keys and DataFrames with patches applied.
    """
    results: dict[str, pl.DataFrame] = {}
    patched_count = 0
    for ticker, df in dfs.items():
        corrected = apply_corrections(df, ticker, config_path)
        results[ticker] = corrected
        if corrected["data_patched"].any():
            patched_count += 1

    logger.info(
        f"[cleaner] apply_corrections_all done: {patched_count} ticker(s) patched."
    )
    return results


def _to_date(value: Any) -> datetime.date:
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))
