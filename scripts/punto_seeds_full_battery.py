"""
Prueba multi-semilla de la batería completa de Bloque 2 (dataset baseline,
features_long.parquet, ya con los Puntos 1-4 del feedback aplicados).

ARIMA y GARCH quedan afuera: su ajuste es optimización por máxima
verosimilitud determinística (sin generador aleatorio), así que repetirlos
con distintas "semillas" no cambiaría el resultado — se reutiliza el ya
corrido (seed=42, resultados oficiales de los Puntos 3/7/8/9).

Los 8 modelos restantes sí dependen de una semilla (RandomizedSearchCV +
aleatoriedad interna del estimador para RF/XGBoost/LightGBM/SVM; init de
pesos + shuffling del DataLoader para las 4 redes). Cada uno importa
RANDOM_STATE directamente en su propio módulo (`from .common import
RANDOM_STATE`), lo que crea un binding local — monkeypatchear
`models.ml.common.RANDOM_STATE` solo alcanza para lo que usa
`tune_and_evaluate` (el random_state de RandomizedSearchCV); el
random_state del estimador en sí (ej. `RandomForestRegressor(random_state=...)`)
vive en el módulo del runner y hay que parchearlo aparte.

Uso: uv run python scripts/punto_seeds_full_battery.py <seed>
"""

from __future__ import annotations

import sys

from config.settings import settings

RESULTS_ROOT = settings.RESULTS_DIR / "punto_seeds"

ML_RUNNERS = ["rf_runner", "svm_runner", "xgboost_runner", "lightgbm_runner"]
DL_RUNNERS = ["lstm_runner", "gru_runner", "cnn_lstm_runner", "tft_lite_runner"]


def run_ml(seed: int) -> None:
    from models.ml import common as ml_common

    ml_common.RANDOM_STATE = seed
    for runner_name in ML_RUNNERS:
        module = __import__(f"models.ml.{runner_name}", fromlist=[runner_name])
        module.RANDOM_STATE = seed
        model_name = runner_name.replace("_runner", "")
        results_dir = RESULTS_ROOT / f"seed{seed}" / "ml" / model_name
        module.main(dataset_name="features_long", results_dir=results_dir)


def run_dl(seed: int) -> None:
    from models.deep_learning import common as dl_common

    dl_common.RANDOM_STATE = seed
    results_dir = RESULTS_ROOT / f"seed{seed}" / "dl"
    for runner_name in DL_RUNNERS:
        module = __import__(f"models.deep_learning.{runner_name}", fromlist=[runner_name])
        module.main(dataset_name="features_long", results_dir=results_dir)


if __name__ == "__main__":
    seed = int(sys.argv[1])
    print(f"=== Semilla {seed}: ML ===")
    run_ml(seed)
    print(f"=== Semilla {seed}: DL ===")
    run_dl(seed)
