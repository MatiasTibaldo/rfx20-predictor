"""
Project-wide configuration via Pydantic BaseSettings.

All values can be overridden by environment variables or a .env file.
The .env file is loaded automatically when the settings object is instantiated.

Design decision: paths are resolved relative to the project root (the directory
that contains this package) rather than the current working directory, so the
pipeline behaves consistently regardless of where it is invoked from.
"""

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root once at import time.
# config/ sits one level below the root, so .parent.parent gives the root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the RFX20 predictor pipeline.

    Attributes:
        PROJECT_ROOT: Absolute path to the repository root.
        DATA_DIR: Base directory for all data layers.
        RAW_DIR: Landing zone for unprocessed source files.
        PROCESSED_DIR: Cleaned / normalised data.
        FEATURES_DIR: Engineered feature sets ready for modelling.
        RESULTS_DIR: Model outputs, evaluation reports, plots.
        DB_PATH: DuckDB database file for experiment tracking.

        PREDICTION_HORIZONS: Forecast horizons in business days.
        ACTIVE_FEATURES: Feature group names to include in the current run.
            Empty list means "no features loaded yet" — modules check this
            before attempting to build feature sets.
        TRAIN_RATIO: Fraction of data used for training.
        VAL_RATIO: Fraction used for validation / hyperparameter search.
        TEST_RATIO: Fraction held out for final evaluation.

        LOG_LEVEL: Loguru-compatible log level string.
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        # Allow extra fields so the .env can carry project-specific secrets
        # (API keys, broker credentials) without breaking validation.
        extra="ignore",
        case_sensitive=False,
    )

    # --- Paths ---
    PROJECT_ROOT: Path = _PROJECT_ROOT
    DATA_DIR: Path = _PROJECT_ROOT / "data"
    RAW_DIR: Path = _PROJECT_ROOT / "data" / "raw"
    PROCESSED_DIR: Path = _PROJECT_ROOT / "data" / "processed"
    FEATURES_DIR: Path = _PROJECT_ROOT / "data" / "features"
    RESULTS_DIR: Path = _PROJECT_ROOT / "results"
    DB_PATH: Path = _PROJECT_ROOT / "results" / "experiments.duckdb"
    SPLITS_CONFIG: Path = _PROJECT_ROOT / "config" / "splits.yaml"

    # --- Modelling ---
    PREDICTION_HORIZONS: list[int] = [1, 3, 5]
    ACTIVE_FEATURES: list[str] = []

    TRAIN_RATIO: float = 0.70
    VAL_RATIO: float = 0.15
    TEST_RATIO: float = 0.15

    # --- Observability ---
    LOG_LEVEL: str = "INFO"

    # --- Primary S.A. API ---
    # Credenciales sensibles: repr=False para que no aparezcan en logs ni en str(settings).
    PRIMARY_USER: str = Field(default="", repr=False)
    PRIMARY_PASS: str = Field(default="", repr=False)
    PRIMARY_BASE_URL: str = Field(default="https://matriz.lbo.xoms.com.ar", repr=False)
    PRIMARY_TIMEOUT: int = 30
    PRIMARY_MAX_RETRIES: int = 3

    # ------------------------------------------------------------------ #
    # Validators                                                           #
    # ------------------------------------------------------------------ #

    @field_validator("TRAIN_RATIO", "VAL_RATIO", "TEST_RATIO")
    @classmethod
    def _ratio_range(cls, v: float) -> float:
        """Ensure each split ratio is in (0, 1)."""
        if not (0 < v < 1):
            raise ValueError(f"Split ratio must be in (0, 1), got {v}")
        return v

    @model_validator(mode="after")
    def _ratios_sum_to_one(self) -> "Settings":
        """Ensure the three split ratios sum to 1.0 (±0.001 tolerance)."""
        total = self.TRAIN_RATIO + self.VAL_RATIO + self.TEST_RATIO
        if abs(total - 1.0) > 1e-3:
            raise ValueError(
                f"TRAIN_RATIO + VAL_RATIO + TEST_RATIO must equal 1.0, got {total:.4f}"
            )
        return self

    @model_validator(mode="after")
    def _ensure_directories(self) -> "Settings":
        """Create data and results directories on first use if missing."""
        for directory in (
            self.RAW_DIR,
            self.PROCESSED_DIR,
            self.FEATURES_DIR,
            self.RESULTS_DIR,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self


# Module-level singleton — import this from other modules instead of
# constructing a new Settings() each time, so .env is only read once.
settings = Settings()
