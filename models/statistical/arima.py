"""
ARIMA/SARIMA baseline for the RFX20 index (Track A, Bloque 2, Etapa 1).

Two distinct steps, deliberately kept separate (see
docs/decisions/arima_baseline_track_a.md):

1. ``select_order`` — grid search over (p,d,q)(P,D,Q,m) by AIC, run ONCE on
   the full train split. This is the expensive, combinatorial step.
2. ``walk_forward_evaluate`` — expanding-window backtest over the val split
   with the order fixed from step 1: each day only re-estimates
   coefficients on the growing history, it never re-runs order selection.
   This keeps a daily refit cheap (~300 fits of a small, fixed-order model)
   instead of re-running the full grid at every step (which would take
   hours for no extra rigor).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import polars as pl
from loguru import logger
from statsmodels.tsa.statespace.sarimax import SARIMAX

HORIZONS = [1, 3, 5]

# 0 = no seasonal component. 5 = weekly (business-day) seasonality — tested
# but not expected to matter much for daily financial returns.
SEASONAL_PERIOD_CANDIDATES = (0, 5)


@dataclass(frozen=True)
class OrderResult:
    """Best (order, seasonal_order) found by select_order, and its AIC."""

    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    aic: float


@dataclass(frozen=True)
class WalkForwardResult:
    """Output of walk_forward_evaluate.

    Attributes:
        predictions: One row per (date, horizon) with y_true/y_pred.
        n_attempted: Number of val dates the walk-forward tried to refit on.
        n_failed: Of those, how many failed to converge and were skipped.
    """

    predictions: pl.DataFrame
    n_attempted: int
    n_failed: int


def _fit_sarimax(
    series: np.ndarray,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
):
    """Fit a single SARIMAX model. Raises on failure to converge — callers decide."""
    model = SARIMAX(
        series,
        order=order,
        seasonal_order=seasonal_order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    return model.fit(disp=False)


def select_order(
    log_return: np.ndarray,
    max_p: int = 5,
    max_q: int = 5,
    d_values: tuple[int, ...] = (0, 1),
    seasonal_periods: tuple[int, ...] = SEASONAL_PERIOD_CANDIDATES,
) -> OrderResult:
    """Grid search (p,d,q)(P,D,Q,m) by AIC, once, on a fixed training window.

    Non-seasonal grid: p, q in [0, max_p]/[0, max_q], d in d_values.
    Seasonal grid: layered on top of the same (p,d,q) grid, restricted to
    P, Q in {0, 1} (D=0 — log-returns don't need seasonal differencing) to
    keep the combinatorial size tractable.

    Args:
        log_return: 1-D array of the training-window log-return series.
        max_p: Max AR order to try.
        max_q: Max MA order to try.
        d_values: Differencing orders to try.
        seasonal_periods: Seasonal periods to try (0 = skip seasonal grid).

    Returns:
        OrderResult for the lowest-AIC candidate that converged.

    Raises:
        RuntimeError: If no candidate converged.
    """
    candidates: list[tuple[tuple[int, int, int], tuple[int, int, int, int]]] = []
    for p, d, q in product(range(max_p + 1), d_values, range(max_q + 1)):
        candidates.append(((p, d, q), (0, 0, 0, 0)))

    for m in seasonal_periods:
        if m == 0:
            continue
        for p, d, q in product(range(max_p + 1), d_values, range(max_q + 1)):
            for seasonal_p, seasonal_q in product((0, 1), (0, 1)):
                if seasonal_p == 0 and seasonal_q == 0:
                    continue
                candidates.append(((p, d, q), (seasonal_p, 0, seasonal_q, m)))

    best: OrderResult | None = None
    n_ok, n_failed = 0, 0
    for order, seasonal_order in candidates:
        try:
            result = _fit_sarimax(log_return, order, seasonal_order)
        except Exception as exc:
            n_failed += 1
            logger.debug(
                f"[arima.select_order] fit failed order={order} "
                f"seasonal={seasonal_order}: {exc}"
            )
            continue
        n_ok += 1
        if best is None or result.aic < best.aic:
            best = OrderResult(order=order, seasonal_order=seasonal_order, aic=result.aic)

    if best is None:
        raise RuntimeError("[arima.select_order] no candidate order converged")

    logger.info(
        f"[arima.select_order] {n_ok} ok / {n_failed} failed of {len(candidates)} candidates. "
        f"Best: order={best.order} seasonal_order={best.seasonal_order} AIC={best.aic:.2f}"
    )
    return best


def walk_forward_evaluate(
    df: pl.DataFrame,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    horizons: list[int] | None = None,
) -> WalkForwardResult:
    """Expanding-window walk-forward backtest over the val split.

    For each date in the val split, fits (order, seasonal_order fixed) on
    every log_return observation up to and including that date (train +
    val-so-far), then forecasts ``max(horizons)`` steps ahead. The forecast
    at step h lands exactly on ``log_return_fwd_h`` of the current date,
    since that column is defined as ``log_return`` shifted -h rows (see
    ``processing/returns.py``) — a single day's return h days ahead, not a
    cumulative h-day return.

    Args:
        df: Must contain ``date``, ``log_return``, ``split``, and
            ``log_return_fwd_{h}`` for each h in horizons, sorted or not
            (sorted internally).
        order: Fixed (p,d,q), typically from ``select_order`` on train.
        seasonal_order: Fixed (P,D,Q,m), typically from ``select_order``.
        horizons: Forecast horizons in business days. Defaults to [1, 3, 5].

    Returns:
        WalkForwardResult with one row per (date, horizon) prediction.
    """
    if horizons is None:
        horizons = HORIZONS

    df = df.sort("date")
    train_val = df.filter(pl.col("split").is_in(["train", "val"]))
    val_dates = df.filter(pl.col("split") == "val")["date"].to_list()

    max_h = max(horizons)
    rows = []
    n_failed = 0

    for current_date in val_dates:
        history = train_val.filter(pl.col("date") <= current_date)["log_return"].to_numpy()
        try:
            result = _fit_sarimax(history, order, seasonal_order)
            forecast = result.get_forecast(steps=max_h).predicted_mean
        except Exception as exc:
            n_failed += 1
            logger.warning(f"[arima.walk_forward] refit failed at {current_date}: {exc}")
            continue

        actual_row = df.filter(pl.col("date") == current_date)
        for h in horizons:
            y_true = actual_row[f"log_return_fwd_{h}"][0]
            rows.append(
                {
                    "date": current_date,
                    "horizon": h,
                    "y_true": y_true,
                    "y_pred": float(forecast[h - 1]),
                }
            )

    predictions = pl.DataFrame(
        rows,
        schema={"date": pl.Date, "horizon": pl.Int64, "y_true": pl.Float64, "y_pred": pl.Float64},
    )
    if n_failed:
        logger.warning(
            f"[arima.walk_forward] {n_failed}/{len(val_dates)} daily refits failed and were skipped."
        )
    logger.info(
        f"[arima.walk_forward] {len(val_dates) - n_failed}/{len(val_dates)} dates refit successfully."
    )
    return WalkForwardResult(
        predictions=predictions, n_attempted=len(val_dates), n_failed=n_failed
    )


def compute_metrics(predictions: pl.DataFrame) -> dict[int, dict[str, float]]:
    """RMSE/MAE per horizon, over rows with a non-null actual value.

    Args:
        predictions: Output of ``walk_forward_evaluate().predictions``.

    Returns:
        Mapping horizon -> {"rmse": ..., "mae": ..., "n": ...}.
    """
    metrics: dict[int, dict[str, float]] = {}
    for h in sorted(predictions["horizon"].unique().to_list()):
        subset = predictions.filter(
            (pl.col("horizon") == h) & pl.col("y_true").is_not_null()
        )
        y_true = subset["y_true"].to_numpy()
        y_pred = subset["y_pred"].to_numpy()
        metrics[h] = {
            "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
            "mae": float(np.mean(np.abs(y_true - y_pred))),
            "n": int(len(y_true)),
        }
    return metrics
