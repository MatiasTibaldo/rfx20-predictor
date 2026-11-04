"""
Punto 8 del feedback de los directores: referencia sencilla de volatilidad
móvil (EWMA, RiskMetrics lambda=0.94) para contextualizar el resultado de
GARCH — hoy solo se compara contra un naive de varianza constante.

EWMA es causal por construcción (sigma2_t depende solo del pasado) y se
recorre una sola vez sobre toda la serie (train+val), a diferencia del
refit diario de GARCH — es, en sí mismo, un benchmark más barato de correr.
Forecast a h días: bajo el mismo supuesto de no-correlación condicional que
ya usa GARCH (ver models/statistical/garch.py), el pronóstico de varianza
acumulada a h días es h * sigma2_t (EWMA no tiene reversión a la media, el
pronóstico de 1 paso se mantiene plano hacia adelante).

Uso: uv run python scripts/punto8_ewma_benchmark.py
"""

from __future__ import annotations

import numpy as np
import polars as pl

from config.settings import settings
from models.statistical.garch import compute_variance_metrics

LAMBDA = 0.94
HORIZONS = [1, 3, 5]


def compute_ewma_variance(log_return: np.ndarray) -> np.ndarray:
    """Causal EWMA variance: sigma2[t] = lambda*sigma2[t-1] + (1-lambda)*r[t-1]**2.

    sigma2[0] seeded with r[0]**2 (first available squared return). Returns
    an array aligned with log_return, where sigma2[t] uses only information
    up to and including r[t-1] — i.e., sigma2[t] is the 1-step-ahead forecast
    made as of t-1, valid to compare against the realization at t.
    """
    sigma2 = np.empty_like(log_return)
    sigma2[0] = log_return[0] ** 2
    for t in range(1, len(log_return)):
        sigma2[t] = LAMBDA * sigma2[t - 1] + (1 - LAMBDA) * log_return[t - 1] ** 2
    return sigma2


def main() -> None:
    df = pl.read_parquet("data/features/v1/features_long.parquet").sort("date")
    log_return = df["log_return"].fill_null(0.0).to_numpy()
    sigma2 = compute_ewma_variance(log_return)

    rows = []
    val_mask = (df["split"] == "val").to_numpy()
    val_idx = np.where(val_mask)[0]
    for h in HORIZONS:
        target_col = f"log_return_fwd_{h}"
        y_true_all = df[target_col].to_numpy()
        for i in val_idx:
            y_true = y_true_all[i]
            if y_true is None or np.isnan(y_true):
                continue
            variance_pred = h * sigma2[i]
            rows.append(
                {
                    "date": df["date"][int(i)],
                    "horizon": h,
                    "variance_pred": float(variance_pred),
                    "sq_return_actual": float(y_true**2),
                }
            )

    predictions = pl.DataFrame(
        rows,
        schema={
            "date": pl.Date,
            "horizon": pl.Int64,
            "variance_pred": pl.Float64,
            "sq_return_actual": pl.Float64,
        },
    )
    metrics = compute_variance_metrics(predictions)

    results_dir = settings.RESULTS_DIR / "punto8_ewma"
    results_dir.mkdir(parents=True, exist_ok=True)
    predictions.write_parquet(results_dir / "ewma_val_predictions.parquet")

    print(f"EWMA (lambda={LAMBDA}) — benchmark de volatilidad móvil\n")
    print(f"{'Horizonte':<10}{'RMSE':<14}{'QLIKE':<14}{'n':<6}")
    for h in HORIZONS:
        m = metrics[h]
        print(f"{h:<10}{m['rmse']:<14.6e}{m['qlike']:<14.6f}{m['n']:<6}")


if __name__ == "__main__":
    main()
