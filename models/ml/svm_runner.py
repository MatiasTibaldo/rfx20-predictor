"""
Entry point for Track A ML, Etapa 1 (Bloque 2 del plan de acción): SVM
(SVR) por horizonte sobre el índice RFX20.

SVR no acepta NaN, así que este runner excluye las columnas con gaps
estructurales reales (futuros, TAMAR, spreads derivados del dólar MEP —
ver docs/decisions/ml_feature_engineering_track_a.md, Decisión 3) del
feature set — Random Forest/XGBoost/LightGBM sí las usan, con sus nulos
reales, en las etapas siguientes.

Uso: uv run python -m models.ml.svm_runner
"""

from __future__ import annotations

import mlflow
import polars as pl
from loguru import logger
from scipy.stats import loguniform
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from config.settings import settings
from storage.store import DuckDBStore

from .common import HORIZONS, RANDOM_STATE, build_model_frame, naive_zero_metrics, split_arrays, tune_and_evaluate

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
RESULTS_DIR = settings.RESULTS_DIR / "track_a_ml" / "svm"

PARAM_DISTRIBUTIONS = {
    "svr__C": loguniform(1e-2, 1e2),
    "svr__gamma": loguniform(1e-4, 1e0),
    "svr__epsilon": loguniform(1e-4, 1e-1),
}


def main() -> None:
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name="features_long", version="v1")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-a-ml")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for h in HORIZONS:
        logger.info(f"[svm_runner] Horizonte {h}: construyendo feature matrix...")
        model_frame = build_model_frame(df, horizon=h, exclude_structural_gaps=True)
        X_train, y_train, feature_names = split_arrays(model_frame, "train")
        X_val, y_val, _ = split_arrays(model_frame, "val")
        logger.info(
            f"[svm_runner] h={h}: train={len(y_train)} filas, val={len(y_val)} filas, "
            f"{len(feature_names)} features"
        )

        pipeline = Pipeline([("scaler", StandardScaler()), ("svr", SVR(kernel="rbf"))])
        result = tune_and_evaluate(
            pipeline,
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

        with mlflow.start_run(run_name=f"svm_h{h}"):
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

    print(f"\n{'Horizonte':<10}{'RMSE (SVM)':<14}{'RMSE (naive)':<14}{'MAE (SVM)':<14}{'MAE (naive)':<14}")
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
