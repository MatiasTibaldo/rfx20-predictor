"""
Backward split adjustment for OHLCV series.

Reads split events, macro events, and dirty-data flags from config/splits.yaml
and exposes them through SplitAdjuster for use in the processing pipeline.

Adjustment convention
---------------------
Backward adjustment: historical prices are modified so the series looks as if
the split never happened from the perspective of the current (post-split) price
level.  For a split with ratio R at date D, every row with date < D has its
OHLC prices multiplied by factor = 1 / R.

Volume is NOT adjusted: the API feed from Primary S.A. already delivers
adjusted volume (split events multiply the traded quantity).

Applying splits in descending date order (most recent first) produces the
correct cumulative adjustment automatically:

  Say ticker has splits at T1 < T2 with ratios R1, R2.
  - Pass 1 (T2, R2): rows before T2 get factor 1/R2.
  - Pass 2 (T1, R1): rows before T1 get an additional factor 1/R1.
  - Result: rows before T1 → factor 1/(R1·R2); rows [T1,T2) → factor 1/R2. ✓

Enforce modes
-------------
enforce_index_only=True  (Enfoque A, default)
    Only apply splits where in_index=True in splits.yaml.
    Suitable when the target variable is the RFX20 index level, where only
    in-index constituents affect index computation.

enforce_index_only=False  (Enfoque B)
    Apply every split for the ticker regardless of index membership.
    Suitable when modelling individual stock returns.
"""

from __future__ import annotations

import datetime
import math
from pathlib import Path
from typing import Any

import polars as pl
import yaml
from loguru import logger

from config.settings import settings


class SplitAdjuster:
    """Load split configuration and apply backward price adjustments to OHLCV data.

    Args:
        config_path: Path to the YAML file. Defaults to ``settings.SPLITS_CONFIG``.

    Attributes:
        _splits: Dict mapping uppercase ticker → list of split dicts, each
            containing keys: ticker, date, ratio, in_index, verified, notes.
        _macro_events: Raw list of macro-event dicts from the YAML.
        _dirty_data: Raw list of dirty-data dicts from the YAML.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or settings.SPLITS_CONFIG
        self._splits: dict[str, list[dict[str, Any]]] = {}
        self._macro_events: list[dict[str, Any]] = []
        self._dirty_data: list[dict[str, Any]] = []
        self._load(path)

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def get_splits_for_ticker(self, ticker: str) -> list[dict[str, Any]]:
        """Return split events for a ticker, sorted by date descending.

        Descending order is the correct application order for backward
        adjustment (most recent split is applied first).

        Args:
            ticker: Instrument symbol (case-insensitive).

        Returns:
            List of split dicts (keys: ticker, date, ratio, in_index,
            verified, notes).  Empty list if no splits exist for the ticker.
        """
        events = self._splits.get(ticker.upper(), [])
        return sorted(events, key=lambda e: e["date"], reverse=True)

    def adjust_series(
        self,
        df: pl.DataFrame,
        ticker: str,
        enforce_index_only: bool = True,
    ) -> pl.DataFrame:
        """Apply backward split adjustment to an OHLCV DataFrame.

        Builds a per-row factor column, then multiplies OHLC prices in a
        single pass.  Volume is left unchanged.

        Factor construction (splits ordered DESC — most recent first):
        - All rows start with factor = 1.0.
        - For each split, the cumulative factor (product of 1/ratio so far) is
          written to every row with date < split_date, overwriting the previous
          value.  Rows above the current boundary keep their existing factor.

        This guarantees the correct stacking behaviour without double-applying:
          date >= s1.date              → factor = 1.0
          s2.date <= date < s1.date    → factor = 1/R1
          date < s2.date               → factor = 1/(R1·R2)

        A ``split_adjusted`` (Boolean) column is appended to the result:
        ``True`` if at least one split was applied, ``False`` otherwise.

        Args:
            df: OHLCV DataFrame.  Must contain a ``date`` column and at
                least one of ``open``, ``high``, ``low``, ``close``.
            ticker: Instrument symbol (case-insensitive).
            enforce_index_only: If ``True`` (Enfoque A), only splits with
                ``in_index=True`` are applied.  If ``False`` (Enfoque B),
                all splits for the ticker are applied.

        Returns:
            DataFrame with adjusted OHLC columns and an appended
            ``split_adjusted`` (Boolean) column.
        """
        splits = self.get_splits_for_ticker(ticker)
        if enforce_index_only:
            splits = [s for s in splits if s["in_index"]]

        if not splits:
            logger.debug(
                f"[SplitAdjuster] {ticker.upper()}: no splits applied "
                f"(enforce_index_only={enforce_index_only})."
            )
            return df.with_columns(pl.lit(False).alias("split_adjusted"))

        price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]

        # --- Build factor column ---
        df = df.with_columns(pl.lit(1.0).alias("_factor"))

        cumulative_factor = 1.0
        applied: list[str] = []

        for split in splits:  # DESC by date — most recent split first
            split_date: datetime.date = split["date"]
            cumulative_factor /= split["ratio"]
            before_split = pl.col("date").cast(pl.Date) < pl.lit(split_date)

            # Overwrite the factor for all rows before this split boundary.
            # Rows in [split_date, next_newer_split) already hold the partial
            # factor from the previous iteration and are left untouched.
            df = df.with_columns(
                pl.when(before_split)
                .then(pl.lit(cumulative_factor))
                .otherwise(pl.col("_factor"))
                .alias("_factor")
            )
            applied.append(f"{split_date}×{1.0 / split['ratio']:.6f}")

        # --- Apply factor to price columns in a single pass ---
        df = df.with_columns(
            [(pl.col(c) * pl.col("_factor")).alias(c) for c in price_cols]
        ).drop("_factor")

        # --- Logging ---
        earliest_split = min(s["date"] for s in splits)
        affected_rows = df.filter(pl.col("date").cast(pl.Date) < pl.lit(earliest_split))
        date_range = (
            f"{affected_rows['date'].min()} → {affected_rows['date'].max()}"
            if len(affected_rows)
            else "no rows"
        )
        logger.info(
            f"[SplitAdjuster] {ticker.upper()}: applied {len(applied)} split(s) "
            f"{applied} | cumulative_factor={cumulative_factor:.6f} "
            f"| affected_rows={len(affected_rows)} ({date_range})"
        )

        return df.with_columns(pl.lit(True).alias("split_adjusted"))

    def adjust_all(
        self,
        dfs: dict[str, pl.DataFrame],
        enforce_index_only: bool = True,
    ) -> dict[str, pl.DataFrame]:
        """Apply split adjustment to every ticker in a dict of DataFrames.

        Args:
            dfs: Mapping of ticker → OHLCV DataFrame.
            enforce_index_only: Forwarded to :meth:`adjust_series`.

        Returns:
            New dict with the same keys and adjusted DataFrames.
        """
        results: dict[str, pl.DataFrame] = {}
        adjusted_count = 0

        for ticker, df in dfs.items():
            result = self.adjust_series(df, ticker, enforce_index_only=enforce_index_only)
            results[ticker] = result
            if result["split_adjusted"][0]:
                adjusted_count += 1

        unchanged = len(dfs) - adjusted_count
        logger.info(
            f"[SplitAdjuster] adjust_all done: "
            f"{adjusted_count} ticker(s) adjusted, {unchanged} unchanged."
        )
        return results

    def get_macro_events(self) -> pl.DataFrame:
        """Return macro events as a Polars DataFrame.

        Useful as a source of dummy variables for the feature engineering module.

        Returns:
            DataFrame with columns:
            ``date`` (Date), ``description`` (String),
            ``tickers_affected`` (List[String]), ``direction`` (String).
        """
        if not self._macro_events:
            return pl.DataFrame(
                schema={
                    "date": pl.Date,
                    "description": pl.String,
                    "tickers_affected": pl.List(pl.String),
                    "direction": pl.String,
                }
            )

        rows = [
            {
                "date": _to_date(e["date"]),
                "description": str(e.get("description", "")),
                "tickers_affected": [str(t) for t in e.get("tickers_affected", [])],
                "direction": str(e.get("direction", "")),
            }
            for e in self._macro_events
        ]
        return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))

    def get_dirty_data(self) -> pl.DataFrame:
        """Return dirty-data records as a Polars DataFrame.

        Used by the processing module to patch known bad values before
        writing to the processed layer.

        Returns:
            DataFrame with columns:
            ``ticker`` (String), ``date`` (Date), ``field`` (String),
            ``value`` (Float64), ``expected_range`` (List[Float64]),
            ``notes`` (String).
        """
        if not self._dirty_data:
            return pl.DataFrame(
                schema={
                    "ticker": pl.String,
                    "date": pl.Date,
                    "field": pl.String,
                    "value": pl.Float64,
                    "expected_range": pl.List(pl.Float64),
                    "notes": pl.String,
                }
            )

        rows = [
            {
                "ticker": str(e["ticker"]).upper(),
                "date": _to_date(e["date"]),
                "field": str(e.get("field", "")),
                "value": float(e.get("value", math.nan)),
                "expected_range": [float(v) for v in e.get("expected_range", [])],
                "notes": str(e.get("notes", "")),
            }
            for e in self._dirty_data
        ]
        return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _load(self, path: Path) -> None:
        """Parse the YAML config and populate internal state."""
        with path.open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}

        for entry in raw.get("splits", []):
            ticker = str(entry["ticker"]).upper()
            event: dict[str, Any] = {
                "ticker": ticker,
                "date": _to_date(entry["date"]),
                "ratio": float(entry["ratio"]),
                "in_index": bool(entry.get("in_index", False)),
                "verified": bool(entry.get("verified", False)),
                "notes": str(entry.get("notes", "")),
            }
            self._splits.setdefault(ticker, []).append(event)

        self._macro_events = raw.get("macro_events", [])
        self._dirty_data = raw.get("dirty_data", [])

        total_splits = sum(len(v) for v in self._splits.values())
        tickers_with_splits = sorted(self._splits.keys())
        logger.info(
            f"[SplitAdjuster] Loaded {total_splits} split(s) "
            f"for {len(tickers_with_splits)} ticker(s): {tickers_with_splits} "
            f"| macro_events={len(self._macro_events)} "
            f"| dirty_data={len(self._dirty_data)}"
        )


def _to_date(value: Any) -> datetime.date:
    """Coerce a YAML date value (already a date, or an ISO string) to datetime.date."""
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value))
