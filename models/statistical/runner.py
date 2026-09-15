"""
Entry point for Track A, Etapa 1 (Bloque 2 del plan de acción): baseline
ARIMA/SARIMA sobre el log-return del índice RFX20.

Uso: uv run python -m models.statistical.runner
"""

from __future__ import annotations

import mlflow
import numpy as np
import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

from .arima import HORIZONS, compute_metrics, select_order, walk_forward_evaluate

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
PREDICTIONS_PATH = settings.RESULTS_DIR / "track_a" / "arima_val_predictions.parquet"


def _naive_zero_metrics(df: pl.DataFrame, horizons: list[int]) -> dict[int, dict[str, float]]:
    """Reference baseline: always predict a return of 0.

    Not a model to select — a sanity floor. If ARIMA/SARIMA can't beat
    "predict nothing happens" on the val split, that's worth knowing before
    moving on to ML/DL models in Bloque 2.
    """
    val = df.filter(pl.col("split") == "val")
    metrics = {}
    for h in horizons:
        y_true = val[f"log_return_fwd_{h}"].drop_nulls().to_numpy()
        metrics[h] = {
            "rmse": float(np.sqrt(np.mean(y_true**2))),
            "mae": float(np.mean(np.abs(y_true))),
            "n": int(len(y_true)),
        }
    return metrics


def main(
    horizons: list[int] | None = None,
    dataset_name: str = "features_long",
    run_name: str = "arima_sarima_baseline",
    predictions_path=PREDICTIONS_PATH,
) -> None:
    horizons = horizons or HORIZONS
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name=dataset_name, version="v1")

    train_log_return = df.filter(pl.col("split") == "train")["log_return"].to_numpy()

    logger.info("[track_a.runner] Selecting (p,d,q)(P,D,Q,m) by AIC on train...")
    order_result = select_order(train_log_return)

    logger.info("[track_a.runner] Running daily-refit walk-forward over val...")
    wf_result = walk_forward_evaluate(
        df, order_result.order, order_result.seasonal_order, horizons=horizons
    )
    arima_metrics = compute_metrics(wf_result.predictions)
    naive_metrics = _naive_zero_metrics(df, horizons)

    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    wf_result.predictions.write_parquet(predictions_path)
    logger.info(f"[track_a.runner] Predictions saved -> {predictions_path}")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-a")
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(
            {
                "order": order_result.order,
                "seasonal_order": order_result.seasonal_order,
                "order_selection_aic": order_result.aic,
                "walk_forward_scheme": "daily_refit_fixed_order",
                "n_val_dates": wf_result.n_attempted,
                "n_failed_refits": wf_result.n_failed,
            }
        )
        for h in horizons:
            mlflow.log_metric(f"rmse_h{h}", arima_metrics[h]["rmse"])
            mlflow.log_metric(f"mae_h{h}", arima_metrics[h]["mae"])
            mlflow.log_metric(f"naive_rmse_h{h}", naive_metrics[h]["rmse"])
            mlflow.log_metric(f"naive_mae_h{h}", naive_metrics[h]["mae"])
        mlflow.log_artifact(str(predictions_path))

    print(f"\nOrden seleccionado: order={order_result.order} "
          f"seasonal_order={order_result.seasonal_order} (AIC={order_result.aic:.2f})")
    print(f"Refits: {wf_result.n_attempted - wf_result.n_failed}/{wf_result.n_attempted} ok\n")
    print(f"{'Horizonte':<10}{'RMSE (ARIMA)':<16}{'RMSE (naive=0)':<16}{'MAE (ARIMA)':<14}{'MAE (naive=0)':<14}")
    for h in horizons:
        a, n = arima_metrics[h], naive_metrics[h]
        print(
            f"{h:<10}{a['rmse']:<16.6f}{n['rmse']:<16.6f}{a['mae']:<14.6f}{n['mae']:<14.6f}"
        )


if __name__ == "__main__":
    main()
