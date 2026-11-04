"""
Punto 5 del feedback de los directores: comparación con un conjunto común de
predictores entre familias (Baseline vs. dataset A — rank top-20 peso+retorno),
usando los runners REALES (no los helpers de prototipo), ya con purge_horizon
activo (Punto 4) y el target acumulado corregido (Punto 3).

Baseline ML (RF/SVM/XGBoost/LightGBM) ya está corrido y persistido por la
re-corrida del Punto 3 (dataset_name="features_long", resultados en
results/track_a_ml/<model>/) — no se repite acá. Solo se corre la variante A
para ML. Para DL (LSTM/GRU/CNN-LSTM/TFT-lite) se corren Baseline-full y
A-full, ambos con feature_set="full", en directorios separados para no pisar
los resultados narrow ya persistidos.

Uso: uv run python scripts/punto5_common_predictor_set.py
"""

from __future__ import annotations

from config.settings import settings
from models.deep_learning.common import FEATURE_SET_FULL

RESULTS_ROOT = settings.RESULTS_DIR


def run_ml_compA() -> None:
    from models.ml import lightgbm_runner, rf_runner, svm_runner, xgboost_runner

    for runner in (rf_runner, svm_runner, xgboost_runner, lightgbm_runner):
        model_name = runner.__name__.split(".")[-1].replace("_runner", "")
        results_dir = RESULTS_ROOT / "track_a_ml_compA" / model_name
        runner.main(dataset_name="features_long_compA", results_dir=results_dir)


def run_dl_full(dataset_name: str, results_subdir: str) -> None:
    from models.deep_learning import cnn_lstm_runner, gru_runner, lstm_runner, tft_lite_runner

    results_dir = RESULTS_ROOT / results_subdir
    for runner in (lstm_runner, gru_runner, cnn_lstm_runner, tft_lite_runner):
        runner.main(
            dataset_name=dataset_name,
            feature_set=FEATURE_SET_FULL,
            results_dir=results_dir,
        )


if __name__ == "__main__":
    import sys

    stage = sys.argv[1] if len(sys.argv) > 1 else "all"

    if stage in ("all", "ml"):
        run_ml_compA()
    if stage in ("all", "dl_baseline"):
        run_dl_full("features_long", "track_b_full_baseline")
    if stage in ("all", "dl_compA"):
        run_dl_full("features_long_compA", "track_b_full_compA")
