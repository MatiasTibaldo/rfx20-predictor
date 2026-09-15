"""
Exploración puntual (no un nodo del pipeline): re-corre los 6 modelos de
Track A sobre horizontes largos (10/21 días hábiles, ~2 semanas / 1 mes),
usando el dataset experimental `features_long_ext.parquet`
(scripts/build_features_long_extended.py) en vez del canónico
`features_long.parquet` — ver docs/decisions/long_horizons_track_a.md.

Condición de salida acordada con el alumno: si ninguno mejora al naive de
forma consistente, se documenta como descartado y se pasa a Track B sin
sumar esto al dataset canónico ni a los runners de corto plazo.

Los modelos de ML usan CV con purge (models.ml.common.purged_splits) para
evitar la fuga por solapamiento de ventanas que no era relevante a h=1/3/5
pero sí lo es acá. ARIMA/GARCH no la necesitan (su walk-forward diario no
tiene ese problema — ver docs/decisions/long_horizons_track_a.md).

Uso: uv run python -m scripts.run_track_a_long_horizons
"""

from __future__ import annotations

from loguru import logger

from config.settings import settings
from models.ml import lightgbm_runner, rf_runner, svm_runner, xgboost_runner
from models.ml.common import LONG_HORIZONS
from models.statistical import garch_runner, runner as arima_runner

DATASET_NAME = "features_long_ext"
RESULTS_ROOT = settings.RESULTS_DIR / "track_a_long_horizons"


def main() -> None:
    logger.info(f"[long_horizons] horizons={LONG_HORIZONS} dataset={DATASET_NAME}")

    logger.info("[long_horizons] === ARIMA/SARIMA ===")
    arima_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        run_name="arima_sarima_long_horizon",
        predictions_path=RESULTS_ROOT / "arima_val_predictions.parquet",
    )

    logger.info("[long_horizons] === GARCH ===")
    garch_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        run_name="garch_long_horizon",
        predictions_path=RESULTS_ROOT / "garch_val_predictions.parquet",
    )

    logger.info("[long_horizons] === SVM ===")
    svm_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        results_dir=RESULTS_ROOT / "svm",
    )

    logger.info("[long_horizons] === Random Forest ===")
    rf_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        results_dir=RESULTS_ROOT / "rf",
    )

    logger.info("[long_horizons] === XGBoost ===")
    xgboost_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        results_dir=RESULTS_ROOT / "xgboost",
    )

    logger.info("[long_horizons] === LightGBM ===")
    lightgbm_runner.main(
        horizons=LONG_HORIZONS,
        dataset_name=DATASET_NAME,
        results_dir=RESULTS_ROOT / "lightgbm",
    )

    logger.info("[long_horizons] Listo — los 6 modelos corrieron para h=10/21.")


if __name__ == "__main__":
    main()
