"""
Entry point para Track B, Etapa 3 (Bloque 2 del plan de acción): híbrido
CNN-LSTM por horizonte sobre el índice RFX20.

Mismo protocolo que models/deep_learning/lstm_runner.py (windowing,
escalado, split de early-stopping, un modelo por horizonte). Etapa 3 corre
sobre el feature set acotado (narrow) — el que no mostró degradación en
Etapa 2 — pero el parámetro queda disponible por consistencia con el resto
de los runners. Ver docs/decisions/track_b_etapa3_tft_hibrido.md.

Uso: uv run python -m models.deep_learning.cnn_lstm_runner
"""

from __future__ import annotations

import mlflow
import polars as pl
from loguru import logger

from config.settings import settings
from models.deep_learning.cnn_lstm import CNNLSTMRegressor
from models.deep_learning.common import (
    FEATURE_SET_NARROW,
    HORIZONS,
    RANDOM_STATE,
    evaluate,
    naive_zero_metrics,
    prepare_frame,
    select_lookback,
)
from storage.store import DuckDBStore

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
RESULTS_DIR = settings.RESULTS_DIR / "track_b"
HIDDEN_SIZE = 32


def main(
    horizons: list[int] | None = None,
    dataset_name: str = "features_long",
    feature_set: str = FEATURE_SET_NARROW,
    results_dir=RESULTS_DIR,
) -> None:
    horizons = horizons or HORIZONS
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name=dataset_name, version="v1")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-b")

    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if feature_set == FEATURE_SET_NARROW else f"_{feature_set}"
    summary_rows = []

    for h in horizons:
        frame, feature_cols, target_col = prepare_frame(df, horizon=h, feature_set=feature_set)
        logger.info(
            f"[cnn_lstm_runner] Horizonte {h} (feature_set={feature_set}, "
            f"{len(feature_cols)} features): grid search de lookback..."
        )
        result = select_lookback(
            frame,
            feature_cols,
            target_col,
            model_factory_for_input_size=lambda n: CNNLSTMRegressor(
                input_size=n, hidden_size=HIDDEN_SIZE
            ),
        )
        logger.info(
            f"[cnn_lstm_runner] h={h}: lookback elegido={result.lookback} "
            f"(best_epoch={result.best_epoch}, earlystop_loss={result.earlystop_loss:.6f})"
        )

        val_rmse, val_mae, dates, y_true, y_pred = evaluate(
            result, frame, feature_cols, target_col, split="val"
        )
        naive_rmse, naive_mae = naive_zero_metrics(y_true)

        predictions_path = results_dir / f"cnn_lstm_val_predictions_h{h}{suffix}.parquet"
        pl.DataFrame({"date": dates, "y_true": y_true, "y_pred": y_pred}).write_parquet(
            predictions_path
        )

        with mlflow.start_run(run_name=f"cnn_lstm_h{h}{suffix}"):
            mlflow.log_params(
                {
                    "horizon": h,
                    "feature_set": feature_set,
                    "n_features": len(feature_cols),
                    "lookback": result.lookback,
                    "hidden_size": HIDDEN_SIZE,
                    "best_epoch": result.best_epoch,
                    "random_state": RANDOM_STATE,
                }
            )
            mlflow.log_metric("earlystop_loss", result.earlystop_loss)
            mlflow.log_metric("val_rmse", val_rmse)
            mlflow.log_metric("val_mae", val_mae)
            mlflow.log_metric("naive_rmse", naive_rmse)
            mlflow.log_metric("naive_mae", naive_mae)
            mlflow.log_artifact(str(predictions_path))

        summary_rows.append(
            {
                "horizon": h,
                "lookback": result.lookback,
                "val_rmse": val_rmse,
                "naive_rmse": naive_rmse,
                "val_mae": val_mae,
                "naive_mae": naive_mae,
            }
        )

    print(
        f"\nCNN-LSTM — feature_set={feature_set}\n"
        f"{'Horizonte':<10}{'Lookback':<10}{'RMSE (CNN-LSTM)':<18}"
        f"{'RMSE (naive)':<14}{'MAE (CNN-LSTM)':<18}{'MAE (naive)':<14}"
    )
    for row in summary_rows:
        print(
            f"{row['horizon']:<10}{row['lookback']:<10}{row['val_rmse']:<18.6f}"
            f"{row['naive_rmse']:<14.6f}{row['val_mae']:<18.6f}{row['naive_mae']:<14.6f}"
        )


if __name__ == "__main__":
    main()
