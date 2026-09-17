"""
Entry point for Track A ML, Etapa 3 (Bloque 2 del plan de acción): XGBoost
por horizonte sobre el índice RFX20.

Igual que Random Forest, XGBoost acepta NaN de forma nativa (manejo de
sparsity/missing incorporado en la búsqueda de splits), así que recibe las
columnas de futuros/TAMAR/MEP con sus nulos reales, sin excluirlas (ver
docs/decisions/ml_feature_engineering_track_a.md, Decisión 3).

Uso: uv run python -m models.ml.xgboost_runner
"""

from __future__ import annotations

import mlflow
import polars as pl
from loguru import logger
from scipy.stats import randint, uniform
from xgboost import XGBRegressor

from config.settings import settings
from storage.store import DuckDBStore

from .common import HORIZONS, RANDOM_STATE, build_model_frame, naive_zero_metrics, split_arrays, tune_and_evaluate

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
RESULTS_DIR = settings.RESULTS_DIR / "track_a_ml" / "xgboost"

PARAM_DISTRIBUTIONS = {
    "n_estimators": randint(100, 600),
    "max_depth": randint(2, 8),
    "learning_rate": uniform(0.01, 0.29),
    "subsample": uniform(0.5, 0.5),
    "colsample_bytree": uniform(0.5, 0.5),
    "reg_lambda": uniform(0.0, 5.0),
}


def main(
    horizons: list[int] | None = None,
    dataset_name: str = "features_long",
    results_dir=RESULTS_DIR,
) -> None:
    horizons = horizons or HORIZONS
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name=dataset_name, version="v1")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-a-ml")

    results_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []

    for h in horizons:
        logger.info(f"[xgboost_runner] Horizonte {h}: construyendo feature matrix...")
        model_frame = build_model_frame(df, horizon=h, exclude_structural_gaps=False)
        X_train, y_train, feature_names, _ = split_arrays(model_frame, "train")
        X_val, y_val, _, dates_val = split_arrays(model_frame, "val")
        logger.info(
            f"[xgboost_runner] h={h}: train={len(y_train)} filas, val={len(y_val)} filas, "
            f"{len(feature_names)} features"
        )

        estimator = XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, tree_method="hist")
        result = tune_and_evaluate(
            estimator,
            PARAM_DISTRIBUTIONS,
            X_train,
            y_train,
            X_val,
            y_val,
            feature_names,
            horizon=h,
        )
        naive_rmse, naive_mae = naive_zero_metrics(y_val)

        importances_path = results_dir / f"importances_h{h}.parquet"
        pl.DataFrame(
            result.importances,
            schema=["feature", "importance_mean", "importance_std"],
            orient="row",
        ).write_parquet(importances_path)

        predictions_path = results_dir / f"xgboost_val_predictions_h{h}.parquet"
        y_pred_val = result.best_estimator.predict(X_val)
        pl.DataFrame({"date": dates_val, "y_true": y_val, "y_pred": y_pred_val}).write_parquet(
            predictions_path
        )

        with mlflow.start_run(run_name=f"xgboost_h{h}"):
            mlflow.log_params({**result.best_params, "horizon": h, "random_state": RANDOM_STATE})
            mlflow.log_metric("cv_best_score_neg_rmse", result.cv_best_score)
            mlflow.log_metric("val_rmse", result.val_rmse)
            mlflow.log_metric("val_mae", result.val_mae)
            mlflow.log_metric("naive_rmse", naive_rmse)
            mlflow.log_metric("naive_mae", naive_mae)
            mlflow.log_artifact(str(importances_path))
            mlflow.log_artifact(str(predictions_path))

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

    print(f"\n{'Horizonte':<10}{'RMSE (XGB)':<14}{'RMSE (naive)':<14}{'MAE (XGB)':<14}{'MAE (naive)':<14}")
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
