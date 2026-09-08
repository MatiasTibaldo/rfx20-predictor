"""
Entry point for Track A ML, Etapa 2 (Bloque 2 del plan de acción): Random
Forest por horizonte sobre el índice RFX20.

A diferencia de SVM, Random Forest (scikit-learn >= 1.4) acepta NaN de
forma nativa, así que recibe las columnas de futuros/TAMAR/MEP con sus
nulos reales, sin excluirlas (ver
docs/decisions/ml_feature_engineering_track_a.md, Decisión 3).

Uso: uv run python -m models.ml.rf_runner
"""

from __future__ import annotations

import mlflow
import polars as pl
from loguru import logger
from scipy.stats import randint, uniform
from sklearn.ensemble import RandomForestRegressor

from config.settings import settings
from storage.store import DuckDBStore

from .common import HORIZONS, RANDOM_STATE, build_model_frame, naive_zero_metrics, split_arrays, tune_and_evaluate

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
RESULTS_DIR = settings.RESULTS_DIR / "track_a_ml" / "rf"

PARAM_DISTRIBUTIONS = {
    "n_estimators": randint(100, 600),
    "max_depth": randint(2, 12),
    "min_samples_leaf": randint(1, 30),
    "max_features": uniform(0.2, 0.8),
}


def main() -> None:
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name="features_long", version="v1")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-a-ml")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for h in HORIZONS:
        logger.info(f"[rf_runner] Horizonte {h}: construyendo feature matrix...")
        model_frame = build_model_frame(df, horizon=h, exclude_structural_gaps=False)
        X_train, y_train, feature_names = split_arrays(model_frame, "train")
        X_val, y_val, _ = split_arrays(model_frame, "val")
        logger.info(
            f"[rf_runner] h={h}: train={len(y_train)} filas, val={len(y_val)} filas, "
            f"{len(feature_names)} features"
        )

        estimator = RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1)
        result = tune_and_evaluate(
            estimator,
            PARAM_DISTRIBUTIONS,
            X_train,
            y_train,
            X_val,
            y_val,
            feature_names,
        )
        naive_rmse, naive_mae = naive_zero_metrics(y_val)

        importances_path = RESULTS_DIR / f"importances_h{h}.parquet"
        pl.DataFrame(
            result.importances,
            schema=["feature", "importance_mean", "importance_std"],
            orient="row",
        ).write_parquet(importances_path)

        with mlflow.start_run(run_name=f"rf_h{h}"):
            mlflow.log_params({**result.best_params, "horizon": h, "random_state": RANDOM_STATE})
            mlflow.log_metric("cv_best_score_neg_rmse", result.cv_best_score)
            mlflow.log_metric("val_rmse", result.val_rmse)
            mlflow.log_metric("val_mae", result.val_mae)
            mlflow.log_metric("naive_rmse", naive_rmse)
            mlflow.log_metric("naive_mae", naive_mae)
            mlflow.log_artifact(str(importances_path))

        summary_rows.append(
            {
                "horizon": h,
                "val_rmse": result.val_rmse,
                "naive_rmse": naive_rmse,
                "val_mae": result.val_mae,
                "naive_mae": naive_mae,
                "top_features": result.importances[:5],
            }
        )

    print(f"\n{'Horizonte':<10}{'RMSE (RF)':<14}{'RMSE (naive)':<14}{'MAE (RF)':<14}{'MAE (naive)':<14}")
    for row in summary_rows:
        print(
            f"{row['horizon']:<10}{row['val_rmse']:<14.6f}{row['naive_rmse']:<14.6f}"
            f"{row['val_mae']:<14.6f}{row['naive_mae']:<14.6f}"
        )
    print()
    for row in summary_rows:
        print(f"Top 5 features (permutation importance), h={row['horizon']}:")
        for feat, mean, std in row["top_features"]:
            print(f"  {feat:<25} {mean:+.6f} (± {std:.6f})")
        print()


if __name__ == "__main__":
    main()
