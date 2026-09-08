"""
GARCH baseline for the RFX20 index (Track A, Bloque 2, Etapa 2).

Unlike ARIMA (Etapa 1, see ``arima.py``), which models the conditional
*mean* of the log-return, GARCH models the conditional *variance* — a
distinct question. Etapa 1 found no exploitable mean structure (best order
(0,0,0), forecast = 0 exactly), which is precisely why the mean here is
fixed at zero (``mean="Zero"``): there is nothing upstream for GARCH to
inherit from an ARIMA mean model.

Design mirrors arima.py's separation of concerns:

1. ``compare_distributions`` — grid search (p,q) by AIC for both a Normal
   and a Student-t innovation distribution, once, on train. Cheap: single
   fits, no walk-forward. Student-t is expected to win given the extreme
   kurtosis found in Etapa 1 (see docs/decisions/arima_baseline_track_a.md)
   — if it does, the Normal distribution is dropped from anything downstream
   (walk-forward, metrics, reports), per an explicit call with the alumno to
   keep this comparison as a quick experimental check, not a parallel track.
2. ``walk_forward_evaluate_variance`` — daily-refit walk-forward over val,
   fixed (p, q, dist), forecasting conditional variance at each horizon.
   Evaluated against squared realized return (log_return_fwd_h ** 2) — the
   standard unbiased (if noisy) proxy for realized variance under a
   zero-mean assumption, chosen because it reuses existing target columns
   instead of requiring a new forward realized-volatility feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import polars as pl
from arch import arch_model
from loguru import logger

HORIZONS = [1, 3, 5]

# arch_model's optimizer is numerically unstable on values as small as raw
# log-returns (~1e-2). Scaling to percentage-like returns before fitting,
# and un-scaling variance forecasts by SCALE**2 afterwards, is the
# standard fix recommended by the library itself (DataScaleWarning).
SCALE = 100.0


@dataclass(frozen=True)
class GarchOrderResult:
    """Best (p, q) found by select_order for a fixed distribution."""

    p: int
    q: int
    dist: str
    aic: float
    loglikelihood: float


@dataclass(frozen=True)
class GarchWalkForwardResult:
    """Output of walk_forward_evaluate_variance.

    Attributes:
        predictions: One row per (date, horizon) with variance_pred (unscaled)
            and sq_return_actual (proxy realized variance).
        n_attempted: Number of val dates the walk-forward tried to refit on.
        n_failed: Of those, how many failed to converge and were skipped.
    """

    predictions: pl.DataFrame
    n_attempted: int
    n_failed: int


def _fit_garch(series_scaled: np.ndarray, p: int, q: int, dist: str):
    """Fit a single zero-mean GARCH(p, q) model. Raises on failure — callers decide."""
    model = arch_model(series_scaled, mean="Zero", vol="GARCH", p=p, q=q, dist=dist)
    return model.fit(disp="off")


def select_order(
    log_return_scaled: np.ndarray,
    dist: str,
    max_p: int = 3,
    max_q: int = 3,
) -> GarchOrderResult:
    """Grid search GARCH(p, q) by AIC, once, on a fixed training window.

    Args:
        log_return_scaled: 1-D array of the training-window log-return
            series, already multiplied by ``SCALE``.
        dist: Innovation distribution passed to ``arch_model`` (e.g.
            ``"normal"`` or ``"t"``).
        max_p: Max GARCH lag (variance equation) to try.
        max_q: Max ARCH lag (squared-residual equation) to try.

    Returns:
        GarchOrderResult for the lowest-AIC candidate that converged.

    Raises:
        RuntimeError: If no candidate converged.
    """
    best: GarchOrderResult | None = None
    n_ok, n_failed = 0, 0
    for p, q in product(range(1, max_p + 1), range(1, max_q + 1)):
        try:
            result = _fit_garch(log_return_scaled, p, q, dist)
        except Exception as exc:
            n_failed += 1
            logger.debug(f"[garch.select_order] fit failed p={p} q={q} dist={dist}: {exc}")
            continue
        n_ok += 1
        if best is None or result.aic < best.aic:
            best = GarchOrderResult(
                p=p, q=q, dist=dist, aic=result.aic, loglikelihood=result.loglikelihood
            )

    if best is None:
        raise RuntimeError(f"[garch.select_order] no candidate converged for dist={dist!r}")

    logger.info(
        f"[garch.select_order] dist={dist!r}: {n_ok} ok / {n_failed} failed. "
        f"Best: GARCH({best.p},{best.q}) AIC={best.aic:.2f}"
    )
    return best


def compare_distributions(
    log_return_scaled: np.ndarray,
    distributions: tuple[str, ...] = ("normal", "t"),
    max_p: int = 3,
    max_q: int = 3,
) -> dict[str, GarchOrderResult]:
    """Run select_order once per distribution, for a quick AIC comparison.

    Args:
        log_return_scaled: 1-D array of the training-window log-return
            series, already multiplied by ``SCALE``.
        distributions: Innovation distributions to compare.
        max_p: Forwarded to select_order.
        max_q: Forwarded to select_order.

    Returns:
        Mapping distribution name -> its best GarchOrderResult.
    """
    results = {}
    for dist in distributions:
        results[dist] = select_order(log_return_scaled, dist, max_p=max_p, max_q=max_q)

    summary = ", ".join(f"{d}: AIC={r.aic:.2f}" for d, r in results.items())
    logger.info(f"[garch.compare_distributions] {summary}")
    return results


def walk_forward_evaluate_variance(
    df: pl.DataFrame,
    p: int,
    q: int,
    dist: str,
    horizons: list[int] | None = None,
) -> GarchWalkForwardResult:
    """Expanding-window walk-forward backtest over the val split.

    For each date in the val split, fits (p, q, dist fixed) on every
    log_return observation up to and including that date (train +
    val-so-far, scaled by SCALE), then forecasts conditional variance
    ``max(horizons)`` steps ahead. Compared against the squared actual
    return at that horizon (``log_return_fwd_h ** 2``) — the standard
    zero-mean proxy for realized variance.

    Args:
        df: Must contain ``date``, ``log_return``, ``split``, and
            ``log_return_fwd_{h}`` for each h in horizons.
        p: Fixed GARCH lag, typically from select_order/compare_distributions.
        q: Fixed ARCH lag.
        dist: Fixed innovation distribution.
        horizons: Forecast horizons in business days. Defaults to [1, 3, 5].

    Returns:
        GarchWalkForwardResult with one row per (date, horizon) prediction.
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
        history = (
            train_val.filter(pl.col("date") <= current_date)["log_return"]
            .drop_nulls()
            .to_numpy()
        )
        try:
            result = _fit_garch(history * SCALE, p, q, dist)
            variance_forecast = (
                result.forecast(horizon=max_h, reindex=False).variance.iloc[-1].to_numpy()
                / SCALE**2
            )
        except Exception as exc:
            n_failed += 1
            logger.warning(f"[garch.walk_forward] refit failed at {current_date}: {exc}")
            continue

        actual_row = df.filter(pl.col("date") == current_date)
        for h in horizons:
            y_true = actual_row[f"log_return_fwd_{h}"][0]
            sq_return_actual = y_true**2 if y_true is not None else None
            rows.append(
                {
                    "date": current_date,
                    "horizon": h,
                    "variance_pred": float(variance_forecast[h - 1]),
                    "sq_return_actual": sq_return_actual,
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
    if n_failed:
        logger.warning(
            f"[garch.walk_forward] {n_failed}/{len(val_dates)} daily refits failed and were skipped."
        )
    logger.info(
        f"[garch.walk_forward] {len(val_dates) - n_failed}/{len(val_dates)} dates refit successfully."
    )
    return GarchWalkForwardResult(
        predictions=predictions, n_attempted=len(val_dates), n_failed=n_failed
    )


def compute_variance_metrics(predictions: pl.DataFrame) -> dict[int, dict[str, float]]:
    """RMSE and QLIKE of the variance forecast, per horizon.

    QLIKE = mean(log(variance_pred) + sq_return_actual / variance_pred) is
    the standard loss function in the volatility-forecasting literature
    (Patton, 2011) — more robust than plain RMSE to how noisy a single
    squared return is as a realized-variance proxy.

    Args:
        predictions: Output of ``walk_forward_evaluate_variance().predictions``,
            or an equivalent DataFrame with a constant ``variance_pred`` for
            a naive baseline.

    Returns:
        Mapping horizon -> {"rmse": ..., "qlike": ..., "n": ...}.
    """
    metrics: dict[int, dict[str, float]] = {}
    for h in sorted(predictions["horizon"].unique().to_list()):
        subset = predictions.filter(
            (pl.col("horizon") == h) & pl.col("sq_return_actual").is_not_null()
        )
        variance_pred = subset["variance_pred"].to_numpy()
        sq_return_actual = subset["sq_return_actual"].to_numpy()
        metrics[h] = {
            "rmse": float(np.sqrt(np.mean((variance_pred - sq_return_actual) ** 2))),
            "qlike": float(np.mean(np.log(variance_pred) + sq_return_actual / variance_pred)),
            "n": int(len(sq_return_actual)),
        }
    return metrics
