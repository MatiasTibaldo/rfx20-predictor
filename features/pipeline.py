"""
Feature engineering pipeline — Etapas 1-2 (technical indicators + realized
volatility per component/index, plus macro features).

Orchestrates loading the processed OHLCV layer and the RFX20 spot series,
computing technical indicators and realized volatility on both, building
the index-level target, consolidating macro features onto the index's
trading calendar, and persisting everything to the features layer.

Deliberately out of scope so far (left for later etapas of Nodo 4, see
docs/plan_de_accion.md): fractional differentiation and the temporal
train/val/test partition. Because of that, output is three intermediate
parquet files rather than the final ``features_long.parquet`` named in the
original plan — that join happens once the temporal split etapa decides
the final schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore
from .macro import build_macro_features
from .target import build_index_target
from .technical import add_technical_indicators, add_technical_indicators_all
from .volatility import add_realized_volatility, add_realized_volatility_all


@dataclass
class FeaturesResult:
    """Summary of a completed features pipeline run.

    Attributes:
        tickers_processed: Component tickers that completed all steps.
        tickers_failed: Component tickers that raised errors during any step.
        components_rows: Row count of the persisted components dataset.
        components_columns: Column count of the persisted components dataset.
        index_rows: Row count of the persisted index dataset.
        index_columns: Column count of the persisted index dataset.
        errors: Mapping of ticker (or ``__index__``) → error message.
    """

    tickers_processed: list[str] = field(default_factory=list)
    tickers_failed: list[str] = field(default_factory=list)
    components_rows: int = 0
    components_columns: int = 0
    index_rows: int = 0
    index_columns: int = 0
    macro_rows: int = 0
    macro_columns: int = 0
    errors: dict[str, str] = field(default_factory=dict)


class FeaturesPipeline:
    """Orchestrate Etapa 1 of Nodo 4: technical indicators + realized volatility.

    Args:
        store: DuckDBStore for Parquet I/O. A default instance is created if None.
        version: Data version tag used for both input and output layers.
        ma_windows: Moving-average / realized-volatility window sizes in
            trading days. Defaults to [10, 20, 50].
        horizons: Forward-return horizons for the index target, in business
            days. Defaults to ``settings.PREDICTION_HORIZONS``.
    """

    def __init__(
        self,
        store: DuckDBStore | None = None,
        version: str = "v1",
        ma_windows: list[int] | None = None,
        horizons: list[int] | None = None,
    ) -> None:
        self._store = store or DuckDBStore()
        self._version = version
        self._ma_windows = ma_windows or [10, 20, 50]
        self._horizons = horizons or list(settings.PREDICTION_HORIZONS)

    def run(self) -> FeaturesResult:
        """Execute the Etapa 1 features pipeline and return a run summary.

        Steps:
            1. Load processed OHLCV long dataset and split by ticker.
            2. Compute technical indicators + realized volatility per ticker.
            3. Persist the recombined long-format components dataset.
            4. Load the RFX20 spot series and build the index target.
            5. Compute technical indicators + realized volatility on the index.
            6. Persist the index-level dataset.

        Returns:
            :class:`FeaturesResult` with per-step summary statistics.
        """
        result = FeaturesResult()

        # --- Step 1: Load processed OHLCV and split by ticker ---
        logger.info("[features] Step 1: Loading processed OHLCV long dataset.")
        try:
            long_df = self._store.load_parquet(
                layer="processed", name="ohlcv_long", version=self._version
            )
        except Exception as exc:
            logger.error(f"[features] Failed to load ohlcv_long: {exc}")
            result.errors["__components__"] = str(exc)
            return result

        dfs = {
            ticker: sub_df
            for (ticker,), sub_df in long_df.partition_by("ticker", as_dict=True).items()
        }
        logger.info(f"[features] Loaded {len(dfs)} tickers from ohlcv_long.")

        # --- Step 2: Technical indicators + realized volatility per ticker ---
        logger.info("[features] Step 2: Computing per-component indicators.")
        try:
            dfs = add_technical_indicators_all(dfs, self._ma_windows)
            dfs = add_realized_volatility_all(dfs, self._ma_windows)
            result.tickers_processed = sorted(dfs.keys())
        except Exception as exc:
            logger.error(f"[features] Failed to compute component indicators: {exc}")
            result.errors["__components__"] = str(exc)
            return result

        # --- Step 3: Persist components dataset ---
        logger.info("[features] Step 3: Persisting components dataset.")
        if dfs:
            components_long = pl.concat(list(dfs.values()), how="diagonal").sort(
                ["date", "ticker"]
            )
            result.components_rows = components_long.height
            result.components_columns = len(components_long.columns)
            self._store.save_parquet(
                components_long,
                layer="features",
                name="technical_components_long",
                version=self._version,
                also_csv=True,
            )

        # --- Step 4: Load RFX20 spot and build index target ---
        logger.info("[features] Step 4: Loading RFX20 spot and building target.")
        try:
            spot_df = self._store.load_parquet(
                layer="raw", name="rfx20_spot", version=self._version
            )
            index_df = build_index_target(spot_df, self._horizons)
        except Exception as exc:
            logger.error(f"[features] Failed to build index target: {exc}")
            result.errors["__index__"] = str(exc)
            return result

        # --- Step 5: Technical indicators + realized volatility on the index ---
        logger.info("[features] Step 5: Computing index-level indicators.")
        try:
            index_df = add_technical_indicators(index_df, self._ma_windows)
            index_df = add_realized_volatility(index_df, self._ma_windows)
        except Exception as exc:
            logger.error(f"[features] Failed to compute index indicators: {exc}")
            result.errors["__index__"] = str(exc)
            return result

        # --- Step 6: Persist index dataset ---
        logger.info("[features] Step 6: Persisting index dataset.")
        result.index_rows = index_df.height
        result.index_columns = len(index_df.columns)
        self._store.save_parquet(
            index_df, layer="features", name="technical_index", version=self._version,
            also_csv=True,
        )

        # --- Step 7: Macro features (non-fatal — Etapa 1 outputs stand alone) ---
        logger.info("[features] Step 7: Computing macro features.")
        try:
            macro_df = build_macro_features(
                index_df["date"], store=self._store, version=self._version
            )
            result.macro_rows = macro_df.height
            result.macro_columns = len(macro_df.columns)
            self._store.save_parquet(
                macro_df, layer="features", name="macro", version=self._version,
                also_csv=True,
            )
        except Exception as exc:
            logger.error(f"[features] Failed to compute macro features: {exc}")
            result.errors["__macro__"] = str(exc)

        logger.info(
            f"[features] Done — components: {len(result.tickers_processed)} tickers, "
            f"{result.components_rows:,} rows; index: {result.index_rows:,} rows; "
            f"macro: {result.macro_rows:,} rows."
        )
        return result
