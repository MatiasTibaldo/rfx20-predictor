"""
Entry point for Track A, Etapa 2 (Bloque 2 del plan de acción): baseline
GARCH sobre la varianza condicional del log-return del índice RFX20.

Uso: uv run python -m models.statistical.garch_runner
"""

from __future__ import annotations

import mlflow
import numpy as np
import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

from .garch import (
    HORIZONS,
    SCALE,
    compare_distributions,
    compute_variance_metrics,
    walk_forward_evaluate_variance,
)

MLRUNS_DB = settings.PROJECT_ROOT / "mlruns.db"
PREDICTIONS_PATH = settings.RESULTS_DIR / "track_a" / "garch_val_predictions.parquet"


def _naive_variance_metrics(
    df: pl.DataFrame, train_variance: float, horizons: list[int]
) -> dict[int, dict[str, float]]:
    """Reference baseline: constant variance = unconditional variance of train.

    The GARCH analogue of ARIMA's "predict return = 0" naive baseline — a
    single fixed number instead of a model that reacts to recent volatility.
    """
    val = df.filter(pl.col("split") == "val")
    metrics = {}
    for h in horizons:
        sq_return_actual = (val[f"log_return_fwd_{h}"].drop_nulls() ** 2).to_numpy()
        variance_pred = np.full_like(sq_return_actual, train_variance)
        metrics[h] = {
            "rmse": float(np.sqrt(np.mean((variance_pred - sq_return_actual) ** 2))),
            "qlike": float(
                np.mean(np.log(variance_pred) + sq_return_actual / variance_pred)
            ),
            "n": int(len(sq_return_actual)),
        }
    return metrics


def main() -> None:
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name="features_long", version="v1")

    train_log_return = df.filter(pl.col("split") == "train")["log_return"].drop_nulls().to_numpy()
    train_variance = float(np.var(train_log_return))

    logger.info(
        "[track_a.garch_runner] Comparing Normal vs Student-t (grid search by AIC on train)..."
    )
    dist_results = compare_distributions(train_log_return * SCALE, distributions=("normal", "t"))

    best_dist = min(dist_results, key=lambda d: dist_results[d].aic)
    best = dist_results[best_dist]
    if best_dist != "t":
        logger.warning(
            "[track_a.garch_runner] La distribución Normal ganó por AIC — "
            "contradice el hallazgo de curtosis extrema de Etapa 1 (ver "
            "docs/decisions/arima_baseline_track_a.md). Revisar antes de "
            "reportar como definitivo."
        )
    logger.info(
        f"[track_a.garch_runner] Distribución elegida: {best_dist!r} "
        f"(GARCH({best.p},{best.q}), AIC={best.aic:.2f}). "
        f"Normal descartada de los informes si {best_dist!r} == 't'."
    )

    logger.info("[track_a.garch_runner] Running daily-refit walk-forward over val...")
    wf_result = walk_forward_evaluate_variance(
        df, best.p, best.q, best.dist, horizons=HORIZONS
    )
    garch_metrics = compute_variance_metrics(wf_result.predictions)
    naive_metrics = _naive_variance_metrics(df, train_variance, HORIZONS)

    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    wf_result.predictions.write_parquet(PREDICTIONS_PATH)
    logger.info(f"[track_a.garch_runner] Predictions saved -> {PREDICTIONS_PATH}")

    mlflow.set_tracking_uri(f"sqlite:///{MLRUNS_DB}")
    mlflow.set_experiment("rfx20-track-a")
    with mlflow.start_run(run_name="garch_baseline"):
        mlflow.log_params(
            {
                "p": best.p,
                "q": best.q,
                "dist": best.dist,
                "order_selection_aic": best.aic,
                "normal_aic": dist_results["normal"].aic,
                "student_t_aic": dist_results["t"].aic,
                "walk_forward_scheme": "daily_refit_fixed_order",
                "n_val_dates": wf_result.n_attempted,
                "n_failed_refits": wf_result.n_failed,
                "train_unconditional_variance": train_variance,
            }
        )
        for h in HORIZONS:
            mlflow.log_metric(f"rmse_var_h{h}", garch_metrics[h]["rmse"])
            mlflow.log_metric(f"qlike_h{h}", garch_metrics[h]["qlike"])
            mlflow.log_metric(f"naive_rmse_var_h{h}", naive_metrics[h]["rmse"])
            mlflow.log_metric(f"naive_qlike_h{h}", naive_metrics[h]["qlike"])
        mlflow.log_artifact(str(PREDICTIONS_PATH))

    print(
        f"\nComparación de distribuciones (grid AIC, train):\n"
        f"  Normal: GARCH({dist_results['normal'].p},{dist_results['normal'].q}) "
        f"AIC={dist_results['normal'].aic:.2f}\n"
        f"  t-Student: GARCH({dist_results['t'].p},{dist_results['t'].q}) "
        f"AIC={dist_results['t'].aic:.2f}\n"
    )
    print(f"Orden seleccionado: GARCH({best.p},{best.q}), dist={best.dist!r} (AIC={best.aic:.2f})")
    print(f"Refits: {wf_result.n_attempted - wf_result.n_failed}/{wf_result.n_attempted} ok\n")
    print(f"{'Horizonte':<10}{'RMSE (GARCH)':<16}{'RMSE (naive)':<16}{'QLIKE (GARCH)':<16}{'QLIKE (naive)':<16}")
    for h in HORIZONS:
        g, n = garch_metrics[h], naive_metrics[h]
        print(
            f"{h:<10}{g['rmse']:<16.6e}{n['rmse']:<16.6e}{g['qlike']:<16.6f}{n['qlike']:<16.6f}"
        )


if __name__ == "__main__":
    main()
