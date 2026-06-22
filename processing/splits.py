"""
Split adjustment for OHLCV series.

Loads split events from config/splits.yaml and applies backward price adjustment
to raw OHLCV Parquet files, writing adjusted files to data/processed/.

Adjustment method: backward (all historical prices before the split date are
divided by the cumulative ratio; volumes are multiplied by the cumulative ratio).

Applying splits oldest-to-newest produces the correct cumulative adjustment:
each subsequent split divides all rows before *its* date, which already includes
the effect of prior splits on earlier rows.

Contrato de entrada  : data/raw/{version}/{ticker}_ohlcv.parquet
Contrato de salida   : data/processed/{version}/{ticker}_ohlcv.parquet
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

_SPLITS_CONFIG = Path(__file__).resolve().parents[1] / "config" / "splits.yaml"


@dataclass(frozen=True)
class SplitEvent:
    """A single split event for a ticker.

    Attributes:
        ticker: Instrument symbol (uppercase).
        date: Effective date of the split in the series.
        ratio: Expansion factor (e.g. 2.0 → 1 share became 2).
        in_index: Whether the ticker was part of the RFX20 on that date.
        verified: Whether the event was manually confirmed.
        notes: Free-text observations.
    """

    ticker: str
    date: datetime.date
    ratio: float
    in_index: bool
    verified: bool
    notes: str = ""


def load_splits(path: Path = _SPLITS_CONFIG) -> dict[str, list[SplitEvent]]:
    """Parse split events from the YAML config, grouped by ticker.

    Args:
        path: Path to the splits YAML file. Defaults to config/splits.yaml.

    Returns:
        Dict mapping ticker (uppercase) to a list of SplitEvent sorted by
        date ascending (oldest first — required for iterative adjustment).
    """
    with path.open("r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)

    result: dict[str, list[SplitEvent]] = {}
    for entry in raw.get("splits", []):
        ticker = str(entry["ticker"]).upper()
        raw_date = entry["date"]
        event_date = (
            raw_date
            if isinstance(raw_date, datetime.date)
            else datetime.date.fromisoformat(str(raw_date))
        )
        event = SplitEvent(
            ticker=ticker,
            date=event_date,
            ratio=float(entry["ratio"]),
            in_index=bool(entry.get("in_index", False)),
            verified=bool(entry.get("verified", False)),
            notes=str(entry.get("notes", "")),
        )
        result.setdefault(ticker, []).append(event)

    for ticker in result:
        result[ticker].sort(key=lambda s: s.date)

    return result


def adjust_ticker(df: pl.DataFrame, splits: list[SplitEvent]) -> pl.DataFrame:
    """Apply backward split adjustment to an OHLCV DataFrame.

    Iterates over splits from oldest to newest. For each split:
    - OHLC prices for rows before the split date are divided by ratio.
    - Volume for rows before the split date is multiplied by ratio.

    This produces the correct cumulative adjustment when multiple splits exist
    for the same ticker: rows before the oldest split end up divided by the
    product of all applicable ratios.

    Args:
        df: OHLCV DataFrame. Must have a ``date`` column and at least one of
            ``open``, ``high``, ``low``, ``close``, or ``volume``.
        splits: Split events for this ticker, sorted by date ascending.

    Returns:
        Adjusted DataFrame with the same schema.
    """
    price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
    has_volume = "volume" in df.columns

    for split in splits:
        before_split = pl.col("date").cast(pl.Date) < pl.lit(split.date)

        adjustments = [
            pl.when(before_split)
            .then(pl.col(c) / split.ratio)
            .otherwise(pl.col(c))
            .alias(c)
            for c in price_cols
        ]
        if has_volume:
            adjustments.append(
                pl.when(before_split)
                .then(pl.col("volume") * split.ratio)
                .otherwise(pl.col("volume"))
                .alias("volume")
            )

        df = df.with_columns(adjustments)
        logger.debug(
            f"  split applied: {split.ticker} @ {split.date} ratio={split.ratio}"
        )

    return df


def run(
    tickers: list[str] | None = None,
    version: str = "v1",
    store: DuckDBStore | None = None,
) -> dict[str, bool]:
    """Apply split adjustments to raw OHLCV Parquet files and save to processed/.

    Tickers without entries in splits.yaml are copied to processed/ without
    modification, ensuring the processed layer is complete regardless of
    whether a ticker had splits.

    Args:
        tickers: Symbols to process. If None, all ``*_ohlcv.parquet`` files
            found in ``data/raw/{version}/`` are processed.
        version: Version tag used for both the input (raw) and output
            (processed) layers (e.g. ``"v1"``).
        store: DuckDBStore instance. If None, one is created with defaults.

    Returns:
        Dict ``{ticker: True/False}`` — True if the ticker was successfully
        read, adjusted (if needed), and written to processed/.
    """
    _store = store or DuckDBStore()
    splits_by_ticker = load_splits()

    if tickers is None:
        raw_dir = settings.RAW_DIR / version
        if not raw_dir.is_dir():
            logger.warning(f"[SplitAdjustment] Raw directory not found: {raw_dir}")
            return {}
        tickers = [
            p.stem.removesuffix("_ohlcv").upper()
            for p in raw_dir.glob("*_ohlcv.parquet")
        ]

    if not tickers:
        logger.warning("[SplitAdjustment] No tickers to process.")
        return {}

    logger.info(
        f"[SplitAdjustment] Processing {len(tickers)} tickers (version={version!r})"
    )

    results: dict[str, bool] = {}
    for ticker in sorted(tickers):
        results[ticker] = _process_ticker(ticker, version, splits_by_ticker, _store)

    ok = sum(results.values())
    failed = len(results) - ok
    logger.info(
        f"[SplitAdjustment] Done | adjusted={ok} failed={failed} total={len(results)}"
    )
    if failed:
        logger.warning(
            f"[SplitAdjustment] Failed tickers: "
            f"{[t for t, ok in results.items() if not ok]}"
        )
    return results


def _process_ticker(
    ticker: str,
    version: str,
    splits_by_ticker: dict[str, list[SplitEvent]],
    store: DuckDBStore,
) -> bool:
    dataset_name = f"{ticker.lower()}_ohlcv"

    try:
        df = store.load_parquet(layer="raw", name=dataset_name, version=version)
    except FileNotFoundError:
        logger.warning(f"[SplitAdjustment] {ticker!r}: raw file not found — skip.")
        return False
    except Exception as exc:
        logger.error(f"[SplitAdjustment] {ticker!r}: failed to load — {exc}")
        return False

    splits = splits_by_ticker.get(ticker, [])
    if splits:
        logger.info(
            f"[SplitAdjustment] {ticker!r}: applying {len(splits)} split(s) "
            f"{[str(s.date) for s in splits]}"
        )
        df = adjust_ticker(df, splits)
    else:
        logger.debug(f"[SplitAdjustment] {ticker!r}: no splits — copying as-is.")

    try:
        store.save_parquet(df, layer="processed", name=dataset_name, version=version)
        return True
    except Exception as exc:
        logger.error(f"[SplitAdjustment] {ticker!r}: failed to save — {exc}")
        return False
