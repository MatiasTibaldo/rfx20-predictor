"""
Shared feature engineering and validation protocol for Track A's classical
ML models (SVM, Random Forest, XGBoost, LightGBM) — Bloque 2 of the plan de
acción.

See docs/decisions/ml_feature_engineering_track_a.md for the full
rationale behind every decision encoded here: one model per horizon,
price-level indicators re-expressed as ratios to close, never imputing
real data gaps (native NaN handling for tree models, feature exclusion for
SVM), and a shared temporal-CV hyperparameter search + permutation
importance protocol so the four model families are comparable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from loguru import logger
from sklearn.inspection import permutation_importance
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit

HORIZONS = [1, 3, 5]
RANDOM_STATE = 42

# Price-level columns (same scale as the index itself, which drifted from
# ~30k to far higher levels over 2018-2026) — re-expressed as a ratio to
# that day's close instead of used as a raw level. See Decisión 2.
PRICE_LEVEL_COLS = ["ma_10", "ma_20", "ma_50", "bb_high", "bb_low", "bb_mid"]

# Real, structural data gaps — never imputed. See Decisión 3 /
# docs/decisions/ml_feature_engineering_track_a.md. Each group starts
# later than train (2018-04-03) for a real, documented reason:
# - futures: no API data before 2020-01-02 (CLAUDE.md / futures_implied_rate.md)
# - tamar: series starts 2024-10-01, ~95% null within train (CLAUDE.md)
# - mep: dolar_mep.csv starts 2018-10-29, ~6 months after train's start
FUTURES_COLS = ["implied_rate_front", "implied_rate_next", "term_spread_futures"]
TAMAR_COLS = ["tamar"]
MEP_COLS = ["spread_oficial_mep", "spread_mep_ccl"]
STRUCTURAL_GAP_GROUPS = {
    "futures_available": FUTURES_COLS,
    "tamar_available": TAMAR_COLS,
    "mep_available": MEP_COLS,
}

# Dropped entirely (not kept, not a feature): the forward-return columns
# that aren't this horizon's target (all are future information) and the
# categorical contract id, which isn't a numeric predictor.
ALWAYS_DROP_COLS = ["log_return_fwd_1", "log_return_fwd_3", "log_return_fwd_5", "futures_front_symbol"]

# Kept in the frame (needed for split filtering) but excluded from the
# feature list in split_arrays — not dropped here like ALWAYS_DROP_COLS.
ID_COLS = ["date", "split"]


def _add_price_ratios(df: pl.DataFrame) -> pl.DataFrame:
    """Replace raw price-level columns with their ratio to close."""
    ratio_exprs = [
        (pl.col(col) / pl.col("close") - 1.0).alias(f"{col}_rel") for col in PRICE_LEVEL_COLS
    ]
    return df.with_columns(ratio_exprs).drop(PRICE_LEVEL_COLS + ["close"])


def _add_availability_flags(df: pl.DataFrame) -> pl.DataFrame:
    """Binary flag per structural-gap group: were all its columns available that day?"""
    flag_exprs = []
    for flag_name, cols in STRUCTURAL_GAP_GROUPS.items():
        available = pl.fold(
            acc=pl.lit(True),
            function=lambda acc, x: acc & x.is_not_null(),
            exprs=[pl.col(c) for c in cols],
        )
        flag_exprs.append(available.cast(pl.Int8).alias(flag_name))
    return df.with_columns(flag_exprs)


def build_model_frame(
    df: pl.DataFrame, horizon: int, exclude_structural_gaps: bool = False
) -> pl.DataFrame:
    """Build the full engineered frame (all splits) for one horizon.

    Args:
        df: Raw ``features_long.parquet`` (all splits together).
        horizon: Which ``log_return_fwd_{h}`` becomes the ``target`` column.
        exclude_structural_gaps: If True (SVM — can't accept NaN), drop the
            futures/TAMAR/MEP-spread columns entirely instead of passing
            their real nulls through. The availability flags stay either
            way (they're never null themselves).

    Returns:
        DataFrame with ``date``, ``split``, ``target``, and every predictor
        column — price-level columns replaced by ``*_rel`` ratios,
        structurally-gapped columns either passed through with real nulls
        (tree models) or dropped (SVM).
    """
    out = _add_price_ratios(df)
    out = _add_availability_flags(out)
    out = out.rename({f"log_return_fwd_{horizon}": "target"})
    drop_cols = [c for c in ALWAYS_DROP_COLS if c in out.columns]
    out = out.drop(drop_cols)

    if exclude_structural_gaps:
        gap_cols = [c for cols in STRUCTURAL_GAP_GROUPS.values() for c in cols]
        out = out.drop(gap_cols)

    return out


def split_arrays(
    model_frame: pl.DataFrame, split: str
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract (X, y, feature_names) for one split ('train' or 'val').

    Rows with any null predictor are dropped, EXCEPT for the
    structurally-gapped columns (futures/TAMAR/MEP-spreads — see
    STRUCTURAL_GAP_GROUPS), whose real nulls are kept for models that
    handle them natively. The remaining nulls dropped here are just
    technical-indicator warm-up at the start of train (~50 rows — see
    docs/decisions/technical_indicators_scope.md).
    """
    subset = model_frame.filter(pl.col("split") == split)
    feature_names = [c for c in subset.columns if c not in ("date", "split", "target")]

    structural_gap_cols = {c for cols in STRUCTURAL_GAP_GROUPS.values() for c in cols}
    non_gap_features = [c for c in feature_names if c not in structural_gap_cols]
    subset = subset.filter(pl.all_horizontal([pl.col(c).is_not_null() for c in non_gap_features]))

    X = subset.select(feature_names).to_numpy()
    y = subset["target"].to_numpy()
    return X, y, feature_names


@dataclass(frozen=True)
class TunedModelResult:
    """Output of tune_and_evaluate: the fitted best estimator and its metrics."""

    best_estimator: object
    best_params: dict
    cv_best_score: float
    val_rmse: float
    val_mae: float
    importances: list[tuple[str, float, float]]  # (feature, mean, std), sorted desc


def temporal_cv(n_splits: int = 5) -> TimeSeriesSplit:
    """Expanding-window time series CV, shared by every model's tuning step."""
    return TimeSeriesSplit(n_splits=n_splits)


def tune_and_evaluate(
    estimator,
    param_distributions: dict,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    feature_names: list[str],
    n_iter: int = 20,
    n_splits: int = 5,
    n_permutation_repeats: int = 20,
) -> TunedModelResult:
    """Shared tuning + evaluation protocol for every Track A ML model.

    Hyperparameters are chosen by RandomizedSearchCV over an expanding-window
    TimeSeriesSplit on train only (val is never used for tuning). The best
    estimator is then evaluated once on val (RMSE/MAE) and its permutation
    importance computed on val, with a fixed random_state throughout for
    exact reproducibility.

    Args:
        estimator: An unfitted sklearn-compatible estimator (or Pipeline).
        param_distributions: Passed to RandomizedSearchCV.
        X_train, y_train: Training arrays (already NaN-filtered per model).
        X_val, y_val: Validation arrays.
        feature_names: Column names matching X's columns, for the
            importance report.
        n_iter: RandomizedSearchCV budget.
        n_splits: TimeSeriesSplit fold count.
        n_permutation_repeats: Permutation importance repeats.

    Returns:
        TunedModelResult with the fitted estimator, chosen params, CV score,
        val metrics, and a feature importance ranking.
    """
    search = RandomizedSearchCV(
        estimator,
        param_distributions=param_distributions,
        n_iter=n_iter,
        cv=temporal_cv(n_splits),
        scoring="neg_root_mean_squared_error",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    best = search.best_estimator_

    y_pred = best.predict(X_val)
    val_rmse = float(np.sqrt(np.mean((y_val - y_pred) ** 2)))
    val_mae = float(np.mean(np.abs(y_val - y_pred)))

    perm = permutation_importance(
        best,
        X_val,
        y_val,
        n_repeats=n_permutation_repeats,
        random_state=RANDOM_STATE,
        scoring="neg_root_mean_squared_error",
    )
    importances = sorted(
        zip(feature_names, perm.importances_mean, perm.importances_std),
        key=lambda t: t[1],
        reverse=True,
    )

    logger.info(
        f"[ml.tune_and_evaluate] best_params={search.best_params_} "
        f"cv_best_score={search.best_score_:.6f} val_rmse={val_rmse:.6f} val_mae={val_mae:.6f}"
    )

    return TunedModelResult(
        best_estimator=best,
        best_params=search.best_params_,
        cv_best_score=float(search.best_score_),
        val_rmse=val_rmse,
        val_mae=val_mae,
        importances=importances,
    )


def naive_zero_metrics(y_val: np.ndarray) -> tuple[float, float]:
    """RMSE/MAE of the same naive baseline used for ARIMA (predict 0)."""
    rmse = float(np.sqrt(np.mean(y_val**2)))
    mae = float(np.mean(np.abs(y_val)))
    return rmse, mae
