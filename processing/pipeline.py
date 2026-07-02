"""
End-to-end processing pipeline for the RFX20 OHLCV data.

Orchestrates split adjustment, data cleaning, index membership tagging,
return computation, dummy variables, and final dataset persistence.
Imports are made directly from submodules to avoid circular imports through
the processing package __init__.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore
from .adjustments import SplitAdjuster
from .cleaner import apply_corrections_all
from .dummies import add_dummies_all
from .filter import add_index_membership_all
from .returns import add_returns_all
from .wide_long import build_long, build_wide
from . import reconstruction as _reconstruction


@dataclass
class ProcessingResult:
    """Summary of a completed processing pipeline run.

    Attributes:
        tickers_processed: Tickers that completed all processing steps.
        tickers_failed: Tickers that raised errors during any step.
        long_rows: Row count of the persisted long-format dataset.
        wide_rows: Row count of the persisted wide-format dataset.
        reconstruction_flagged: Days where the reconstructed index exceeded
            the validation tolerance. None if reconstruction was skipped.
        errors: Mapping of ticker (or ``__reconstruction__``) → error message.
    """

    tickers_processed: list[str] = field(default_factory=list)
    tickers_failed: list[str] = field(default_factory=list)
    long_rows: int = 0
    wide_rows: int = 0
    reconstruction_flagged: int | None = None
    errors: dict[str, str] = field(default_factory=dict)


class ProcessingPipeline:
    """Orchestrate the full Nodo 3 processing workflow.

    Args:
        store: DuckDBStore for Parquet I/O. A default instance is created if None.
        version: Data version tag used for both input and output layers.
        config_path: Path to splits.yaml. Defaults to ``settings.SPLITS_CONFIG``.
        enforce_index_only: Enfoque A (True, default) applies splits only for
            tickers in-index on the split date.
        horizons: Forward-return prediction horizons in business days.
        run_reconstruction: If True, also run index reconstruction and validation.
        divisores_path: Path to ``divisores.csv`` for the reconstruction step.
        reconstruction_tolerance_pct: Flagging threshold for validation.
    """

    def __init__(
        self,
        store: DuckDBStore | None = None,
        version: str = "v1",
        config_path: Path | None = None,
        enforce_index_only: bool = True,
        horizons: list[int] | None = None,
        run_reconstruction: bool = False,
        divisores_path: Path | None = None,
        reconstruction_tolerance_pct: float = 1.0,
    ) -> None:
        self._store = store or DuckDBStore()
        self._version = version
        self._config_path = config_path or settings.SPLITS_CONFIG
        self._enforce_index_only = enforce_index_only
        self._horizons = horizons or list(settings.PREDICTION_HORIZONS)
        self._do_reconstruction = run_reconstruction
        self._divisores_path = divisores_path
        self._reconstruction_tolerance_pct = reconstruction_tolerance_pct

    def run(self) -> ProcessingResult:
        """Execute the processing pipeline and return a run summary.

        Steps:
            1. Load raw OHLCV for all tickers.
            2. Load index composition.
            3. Apply split adjustments (SplitAdjuster.adjust_all).
            4. Patch known dirty data (apply_corrections_all).
            5. Tag index membership (add_index_membership_all).
            6. Compute returns (add_returns_all).
            7. Add dummy variables (add_dummies_all).
            8. Persist long and wide datasets.
            9. (Optional) Reconstruct index and validate against spot.

        Returns:
            :class:`ProcessingResult` with per-step summary statistics.
        """
        result = ProcessingResult()

        # --- Step 1: Load raw OHLCV ---
        logger.info("[pipeline] Step 1: Loading raw OHLCV files.")
        raw_dir = settings.RAW_DIR / self._version
        ohlcv_paths = sorted(raw_dir.glob("*_ohlcv.parquet"))
        if not ohlcv_paths:
            logger.warning(f"[pipeline] No OHLCV files found in {raw_dir}.")
            return result

        dfs: dict[str, pl.DataFrame] = {}
        for path in ohlcv_paths:
            ticker = path.stem.removesuffix("_ohlcv").upper()
            try:
                dfs[ticker] = self._store.load_parquet(
                    layer="raw",
                    name=f"{ticker.lower()}_ohlcv",
                    version=self._version,
                )
            except Exception as exc:
                logger.error(f"[pipeline] Failed to load {ticker}: {exc}")
                result.tickers_failed.append(ticker)
                result.errors[ticker] = str(exc)

        logger.info(f"[pipeline] Loaded {len(dfs)} tickers.")

        # --- Step 2: Load composition ---
        logger.info("[pipeline] Step 2: Loading index composition.")
        try:
            composition = self._store.load_parquet(
                layer="raw", name="rfx20_composition", version=self._version
            )
        except Exception as exc:
            logger.error(f"[pipeline] Failed to load composition: {exc}")
            return result

        # --- Step 3: Split adjustments ---
        logger.info("[pipeline] Step 3: Applying split adjustments.")
        adjuster = SplitAdjuster(self._config_path)
        dfs = adjuster.adjust_all(dfs, enforce_index_only=self._enforce_index_only)

        # --- Step 4: Data corrections ---
        logger.info("[pipeline] Step 4: Patching known dirty data.")
        dfs = apply_corrections_all(dfs, self._config_path)

        # --- Step 5: Index membership ---
        logger.info("[pipeline] Step 5: Tagging index membership.")
        dfs = add_index_membership_all(dfs, composition)

        # --- Step 6: Returns ---
        logger.info("[pipeline] Step 6: Computing returns.")
        dfs = add_returns_all(dfs, self._horizons)

        # --- Step 7: Dummy variables ---
        logger.info("[pipeline] Step 7: Adding dummy variables.")
        dfs = add_dummies_all(dfs, self._config_path)

        result.tickers_processed = sorted(dfs.keys())

        # --- Step 8: Persist datasets ---
        logger.info("[pipeline] Step 8: Persisting long and wide datasets.")
        long_df = build_long(dfs)
        wide_df = build_wide(dfs)
        result.long_rows = long_df.height
        result.wide_rows = wide_df.height
        self._store.save_parquet(
            long_df, layer="processed", name="ohlcv_long", version=self._version
        )
        self._store.save_parquet(
            wide_df, layer="processed", name="ohlcv_wide", version=self._version
        )

        # --- Step 9: Reconstruction (optional) ---
        if self._do_reconstruction:
            logger.info("[pipeline] Step 9: Running index reconstruction.")
            try:
                validation_df = _reconstruction.run(
                    ohlcv_by_ticker=dfs,
                    composition=composition,
                    store=self._store,
                    version=self._version,
                    divisores_path=self._divisores_path,
                    tolerance_pct=self._reconstruction_tolerance_pct,
                )
                result.reconstruction_flagged = validation_df.filter(
                    pl.col("flag")
                ).height
            except Exception as exc:
                logger.error(f"[pipeline] Reconstruction failed: {exc}")
                result.errors["__reconstruction__"] = str(exc)

        logger.info(
            f"[pipeline] Done — processed={len(result.tickers_processed)}, "
            f"failed={len(result.tickers_failed)}, "
            f"long_rows={result.long_rows:,}, wide_rows={result.wide_rows:,}."
        )
        return result
