"""
DuckDB + Parquet persistence layer for the RFX20 pipeline.

Responsibilities:
- Save and load Polars DataFrames as versioned Parquet files in the
  appropriate data layer directory (raw / processed / features).
- Persist experiment metadata (model name, hyperparameters, metrics) to
  a DuckDB database so runs can be compared programmatically.

Design decisions:
- DuckDB is used *only* for experiment tracking (the runs table).
  Actual data lives in Parquet files; DuckDB can query them directly
  via its Parquet reader, but we keep that optional for flexibility.
- Connections are opened and closed per operation (no persistent
  connection held open) to avoid cross-thread issues during notebook use.
- Polars is the primary DataFrame library; pandas conversion is available
  but not the default path.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import duckdb
import polars as pl
from loguru import logger

from config.settings import settings

# Valid data layer names — used for type-checking and path resolution.
Layer = Literal["raw", "processed", "features"]

_LAYER_DIRS: dict[Layer, Path] = {
    "raw": settings.RAW_DIR,
    "processed": settings.PROCESSED_DIR,
    "features": settings.FEATURES_DIR,
}


class DuckDBStore:
    """Unified storage interface for data files and experiment logs.

    Args:
        db_path: Path to the DuckDB file used for experiment tracking.
            Defaults to ``settings.DB_PATH``.

    Example:
        >>> store = DuckDBStore()
        >>> store.save_parquet(df, layer="processed", name="rfx20_ohlcv", version="v1")
        >>> df = store.load_parquet(layer="processed", name="rfx20_ohlcv", version="v1")
        >>> store.log_run("LinearRegression", {"alpha": 0.1}, {"rmse": 0.05})
        >>> runs = store.load_runs()
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.DB_PATH
        self._init_db()

    # ------------------------------------------------------------------ #
    # Parquet helpers                                                      #
    # ------------------------------------------------------------------ #

    def _parquet_path(self, layer: Layer, name: str, version: str) -> Path:
        """Build the full path for a versioned Parquet file."""
        directory = _LAYER_DIRS[layer]
        # version subdirectory keeps multiple versions of the same dataset
        # side-by-side without overwriting (e.g. data/processed/v1/rfx20_ohlcv.parquet)
        versioned_dir = directory / version
        versioned_dir.mkdir(parents=True, exist_ok=True)
        return versioned_dir / f"{name}.parquet"

    def save_parquet(
        self,
        df: pl.DataFrame,
        layer: Layer,
        name: str,
        version: str = "v1",
    ) -> Path:
        """Persist a Polars DataFrame as a Parquet file.

        Args:
            df: DataFrame to save.
            layer: Data layer — one of ``raw``, ``processed``, ``features``.
            name: Logical dataset name (e.g. ``"rfx20_ohlcv"``).
            version: Version tag used to namespace the file (e.g. ``"v1"``).

        Returns:
            The resolved path where the file was written.

        Raises:
            ValueError: If ``layer`` is not a recognised layer name.
            Exception: Re-raised after logging on any I/O error.
        """
        if layer not in _LAYER_DIRS:
            raise ValueError(f"Unknown layer '{layer}'. Choose from {list(_LAYER_DIRS)}")

        path = self._parquet_path(layer, name, version)
        try:
            df.write_parquet(path)
            logger.info(f"Saved {len(df):,} rows → {path}")
        except Exception as exc:
            logger.error(f"Failed to save parquet [{layer}/{version}/{name}]: {exc}")
            raise
        return path

    def load_parquet(
        self,
        layer: Layer,
        name: str,
        version: str = "v1",
    ) -> pl.DataFrame:
        """Load a versioned Parquet file into a Polars DataFrame.

        Args:
            layer: Data layer — one of ``raw``, ``processed``, ``features``.
            name: Logical dataset name.
            version: Version tag (must match the one used when saving).

        Returns:
            Polars DataFrame with the stored data.

        Raises:
            FileNotFoundError: If the requested file does not exist.
            Exception: Re-raised after logging on any I/O error.
        """
        if layer not in _LAYER_DIRS:
            raise ValueError(f"Unknown layer '{layer}'. Choose from {list(_LAYER_DIRS)}")

        path = self._parquet_path(layer, name, version)
        if not path.exists():
            raise FileNotFoundError(
                f"Parquet file not found: {path}\n"
                f"  layer={layer!r}, name={name!r}, version={version!r}"
            )
        try:
            df = pl.read_parquet(path)
            logger.info(f"Loaded {len(df):,} rows ← {path}")
        except Exception as exc:
            logger.error(f"Failed to load parquet [{layer}/{version}/{name}]: {exc}")
            raise
        return df

    # ------------------------------------------------------------------ #
    # Experiment tracking                                                  #
    # ------------------------------------------------------------------ #

    def _init_db(self) -> None:
        """Create the experiment tracking table if it does not exist."""
        try:
            with duckdb.connect(str(self.db_path)) as con:
                con.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id      INTEGER PRIMARY KEY,
                        model_name  VARCHAR NOT NULL,
                        params      JSON,
                        metrics     JSON,
                        created_at  TIMESTAMPTZ DEFAULT now()
                    )
                """)
            logger.debug(f"Experiment DB ready at {self.db_path}")
        except Exception as exc:
            logger.error(f"Failed to initialise experiment DB: {exc}")
            raise

    def log_run(
        self,
        model_name: str,
        params: dict,
        metrics: dict,
    ) -> int:
        """Record an experiment run in DuckDB.

        Args:
            model_name: Identifier for the model (e.g. ``"RandomForest"``).
            params: Hyperparameters used in this run.
            metrics: Evaluation metrics (e.g. ``{"rmse": 0.05, "mae": 0.03}``).

        Returns:
            The ``run_id`` assigned to the new record.

        Raises:
            Exception: Re-raised after logging on DB error.
        """
        try:
            with duckdb.connect(str(self.db_path)) as con:
                result = con.execute(
                    """
                    INSERT INTO runs (model_name, params, metrics, created_at)
                    VALUES (?, ?, ?, ?)
                    RETURNING run_id
                    """,
                    [
                        model_name,
                        json.dumps(params),
                        json.dumps(metrics),
                        datetime.now(tz=timezone.utc),
                    ],
                ).fetchone()
            run_id: int = result[0]
            logger.info(f"Logged run #{run_id} — model={model_name!r} metrics={metrics}")
            return run_id
        except Exception as exc:
            logger.error(f"Failed to log run for {model_name!r}: {exc}")
            raise

    def load_runs(
        self,
        model_name: str | None = None,
    ) -> pl.DataFrame:
        """Retrieve logged experiment runs as a Polars DataFrame.

        Args:
            model_name: Optional filter to return only runs for a specific
                model. If ``None``, all runs are returned.

        Returns:
            DataFrame with columns:
            ``run_id``, ``model_name``, ``params``, ``metrics``, ``created_at``.

        Raises:
            Exception: Re-raised after logging on DB error.
        """
        try:
            with duckdb.connect(str(self.db_path)) as con:
                if model_name:
                    arrow = con.execute(
                        "SELECT * FROM runs WHERE model_name = ? ORDER BY run_id",
                        [model_name],
                    ).arrow()
                else:
                    arrow = con.execute(
                        "SELECT * FROM runs ORDER BY run_id"
                    ).arrow()
            df = pl.from_arrow(arrow)
            logger.debug(f"Loaded {len(df)} run(s) from experiment DB")
            return df
        except Exception as exc:
            logger.error(f"Failed to load runs: {exc}")
            raise
