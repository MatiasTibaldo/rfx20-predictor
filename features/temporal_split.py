"""
Temporal train/val/test split for the RFX20 feature tables.

Chronological only — never shuffled. Shuffling a time series split leaks
future information into training (a row's temporal neighbors would appear
on both sides of the split).
"""

from __future__ import annotations

from datetime import date

import polars as pl
from loguru import logger


def add_temporal_split(
    dates: pl.Series,
    test_start: date | None = None,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> pl.DataFrame:
    """Assign each date to train/val/test, preserving chronological order.

    Two modes:

    - ``test_start`` given: every date >= ``test_start`` is test (meant for
      genuinely out-of-sample data — see docs/decisions/rfx20_ws_backfill.md).
      The remaining, earlier dates are split between train and val using
      ``train_ratio`` renormalized against ``train_ratio + val_ratio``
      (``test_ratio`` is ignored in this mode).
    - ``test_start`` omitted: pure chronological split over the full range
      using ``train_ratio`` / ``val_ratio`` / ``test_ratio`` directly (must
      sum to 1.0).

    Args:
        dates: Date column to split, any order (sorted internally).
        test_start: If given, the fixed cutoff — dates on or after this are
            test, regardless of ratio.
        train_ratio: Train fraction (see modes above for how it's applied).
        val_ratio: Val fraction.
        test_ratio: Test fraction (only used when ``test_start`` is None).

    Returns:
        DataFrame with columns ``date`` and ``split`` (``"train"``,
        ``"val"``, or ``"test"``), sorted by date.
    """
    unique_dates = dates.unique().sort()
    n = len(unique_dates)

    if test_start is not None:
        historical = unique_dates.filter(unique_dates < test_start)
        test_dates = unique_dates.filter(unique_dates >= test_start)

        train_frac = train_ratio / (train_ratio + val_ratio)
        train_end = int(len(historical) * train_frac)

        train_dates = historical[:train_end]
        val_dates = historical[train_end:]
    else:
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError(
                f"train_ratio + val_ratio + test_ratio must sum to 1.0, "
                f"got {train_ratio + val_ratio + test_ratio}"
            )
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        train_dates = unique_dates[:train_end]
        val_dates = unique_dates[train_end:val_end]
        test_dates = unique_dates[val_end:]

    result = pl.concat(
        [
            pl.DataFrame({"date": train_dates}).with_columns(pl.lit("train").alias("split")),
            pl.DataFrame({"date": val_dates}).with_columns(pl.lit("val").alias("split")),
            pl.DataFrame({"date": test_dates}).with_columns(pl.lit("test").alias("split")),
        ]
    ).sort("date")

    logger.info(
        f"[temporal_split] train={len(train_dates):,} "
        f"({train_dates[0]}→{train_dates[-1] if len(train_dates) else '—'}), "
        f"val={len(val_dates):,} "
        f"({val_dates[0] if len(val_dates) else '—'}→{val_dates[-1] if len(val_dates) else '—'}), "
        f"test={len(test_dates):,} "
        f"({test_dates[0] if len(test_dates) else '—'}→{test_dates[-1] if len(test_dates) else '—'})"
    )
    return result
