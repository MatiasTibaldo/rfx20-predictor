"""
Shared windowing/scaling/training protocol for Track B's deep learning
models (LSTM, GRU, ...) — Bloque 2 of the plan de acción.

See docs/decisions/lstm_baseline_track_b.md (Etapa 1) for the original
rationale: a bounded feature set (log-return + realized volatility, no
macro, no technical indicators) as a first baseline, one model per
horizon (same convention as Track A), sliding lookback windows built over
the full timeline (val/test windows may look back into train rows — those
are real past values, not label leakage, the same logic as the
technical-indicator warm-up at the start of train), StandardScaler fit on
train windows only, and an early-stopping split carved out of the
chronological tail of train so the real `val` split stays untouched — an
apples-to-apples comparison against every Track A model, none of which
ever tuned against `val` either (see models/ml/common.py::tune_and_evaluate).

See docs/decisions/track_b_etapa2_gru_full_features.md (Etapa 2) for the
"full" feature set: reuses models.ml.common.build_model_frame exactly as
SVM does (price-level columns re-expressed as ratios to close, structural
gaps — futures/TAMAR/MEP — excluded entirely rather than imputed, since
neither SVM nor a plain LSTM/GRU can accept NaN inputs without fabricating
values, which the project forbids).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
import torch
from loguru import logger
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from models.ml.common import HORIZONS, RANDOM_STATE, build_model_frame, naive_zero_metrics

__all__ = [
    "HORIZONS",
    "RANDOM_STATE",
    "naive_zero_metrics",
    "WINDOW_FEATURES",
    "LOOKBACK_CANDIDATES",
    "FEATURE_SET_NARROW",
    "FEATURE_SET_FULL",
    "Sequences",
    "prepare_frame",
    "build_sequences",
    "scale_sequences",
    "TrainResult",
    "train_with_early_stopping",
    "select_lookback",
    "evaluate",
]

# Etapa 1 baseline: price/return + realized volatility only, no macro, no
# technical indicators (RSI/MACD/Bollinger) — a clean first baseline before
# deciding whether the added complexity of the full Track A feature set
# earns its keep. See prepare_frame() for the Etapa 2 "full" alternative.
WINDOW_FEATURES = ["log_return", "realized_vol_10", "realized_vol_20", "realized_vol_50"]

FEATURE_SET_NARROW = "narrow"
FEATURE_SET_FULL = "full"

# Chosen empirically per horizon (see select_lookback), anchored to the
# window lengths already used elsewhere in the project for MA/volatility.
LOOKBACK_CANDIDATES = [10, 20, 30]

# Fraction of train (chronologically, the tail) held out for early
# stopping. The real `val` split is never touched during model selection.
EARLYSTOP_FRACTION = 0.15


@dataclass(frozen=True)
class Sequences:
    """One split's windowed arrays for a given (horizon, lookback)."""

    X: np.ndarray  # (n, lookback, n_features)
    y: np.ndarray  # (n,)
    dates: np.ndarray  # (n,) — anchor date of each window (last day in the window)


def prepare_frame(
    df: pl.DataFrame, horizon: int, feature_set: str = FEATURE_SET_NARROW
) -> tuple[pl.DataFrame, list[str], str]:
    """Build the (frame, feature_cols, target_col) triple for one horizon.

    Args:
        df: Full features_long.parquet (all splits together).
        horizon: Forecast horizon in business days.
        feature_set: FEATURE_SET_NARROW (Etapa 1: log_return + realized
            volatility) or FEATURE_SET_FULL (Etapa 2: every Track A ML
            predictor, same treatment as SVM — price ratios, structural
            gaps excluded entirely rather than imputed).

    Returns:
        (frame sorted by date, feature column names, target column name).
    """
    if feature_set == FEATURE_SET_NARROW:
        return df.sort("date"), list(WINDOW_FEATURES), f"log_return_fwd_{horizon}"
    if feature_set == FEATURE_SET_FULL:
        frame = build_model_frame(df, horizon=horizon, exclude_structural_gaps=True).sort("date")
        feature_cols = [c for c in frame.columns if c not in ("date", "split", "target")]
        return frame, feature_cols, "target"
    raise ValueError(f"feature_set desconocido: {feature_set!r}")


def build_sequences(
    frame: pl.DataFrame, feature_cols: list[str], target_col: str, lookback: int
) -> dict[str, Sequences]:
    """Build sliding-window sequences per split for one (frame, lookback).

    Each window anchors on a row's own date/split (same convention as
    models.ml.common.build_model_frame) and predicts that row's target.
    The window itself may reach back past the split boundary into earlier
    rows — those are real historical values, not future information, so
    this isn't leakage.

    Args:
        frame: Output of prepare_frame — already sorted by date.
        feature_cols: Predictor column names.
        target_col: Target column name.
        lookback: Number of past days (inclusive of the anchor day) per window.

    Returns:
        Dict with keys "train", "val", "test", each a Sequences of that split.
    """
    feats = frame.select(feature_cols).to_numpy().astype(np.float64)
    targets = frame[target_col].to_numpy()
    dates = frame["date"].to_numpy()
    splits = frame["split"].to_numpy()

    valid_row = ~np.isnan(feats).any(axis=1)

    n = len(frame)
    X_list, y_list, date_list, split_list = [], [], [], []
    for i in range(lookback - 1, n):
        target = targets[i]
        if np.isnan(target):
            continue
        window_rows = valid_row[i - lookback + 1 : i + 1]
        if not window_rows.all():
            continue
        X_list.append(feats[i - lookback + 1 : i + 1])
        y_list.append(target)
        date_list.append(dates[i])
        split_list.append(splits[i])

    X = np.stack(X_list).astype(np.float32)
    y = np.array(y_list, dtype=np.float32)
    dates_arr = np.array(date_list)
    split_arr = np.array(split_list)

    out = {}
    for split_name in ("train", "val", "test"):
        mask = split_arr == split_name
        out[split_name] = Sequences(X=X[mask], y=y[mask], dates=dates_arr[mask])
    return out


def scale_sequences(
    fit_X: np.ndarray, *other_X: np.ndarray
) -> tuple[StandardScaler, list[np.ndarray]]:
    """Fit a StandardScaler on fit_X (per-feature, across all timesteps) and
    apply it to fit_X and every array in other_X.

    Same intent as the StandardScaler inside svm_runner.py's Pipeline, just
    applied to 3-D windowed arrays: flatten to (n*lookback, n_features),
    scale, reshape back.
    """
    n_features = fit_X.shape[-1]
    scaler = StandardScaler()
    scaler.fit(fit_X.reshape(-1, n_features))

    def _apply(X: np.ndarray) -> np.ndarray:
        shape = X.shape
        return scaler.transform(X.reshape(-1, n_features)).reshape(shape).astype(np.float32)

    return scaler, [_apply(fit_X)] + [_apply(X) for X in other_X]


def chronological_earlystop_split(seq: Sequences, fraction: float = EARLYSTOP_FRACTION):
    """Split train Sequences into (fit, earlystop) by chronological tail.

    Sequences are already date-ordered (build_sequences sorts df by date
    before windowing), so the last `fraction` of rows is the most recent
    slice of train.
    """
    n = len(seq.y)
    cut = int(round(n * (1.0 - fraction)))
    fit = Sequences(X=seq.X[:cut], y=seq.y[:cut], dates=seq.dates[:cut])
    earlystop = Sequences(X=seq.X[cut:], y=seq.y[cut:], dates=seq.dates[cut:])
    return fit, earlystop


@dataclass
class TrainResult:
    model: nn.Module
    scaler: StandardScaler
    lookback: int
    best_epoch: int
    earlystop_loss: float
    history: list[float]


def train_with_early_stopping(
    model_factory,
    X_fit: np.ndarray,
    y_fit: np.ndarray,
    X_earlystop: np.ndarray,
    y_earlystop: np.ndarray,
    lr: float = 1e-3,
    max_epochs: int = 200,
    patience: int = 15,
    batch_size: int = 64,
) -> tuple[nn.Module, int, float, list[float]]:
    """Train model_factory() with early stopping on (X_earlystop, y_earlystop).

    Seeds torch before construction/training for reproducibility (CLAUDE.md
    requires it for model code). Returns the best-epoch model state (lowest
    early-stopping loss), not the last epoch's.
    """
    torch.manual_seed(RANDOM_STATE)
    model = model_factory()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    train_ds = TensorDataset(torch.from_numpy(X_fit), torch.from_numpy(y_fit))
    loader_generator = torch.Generator().manual_seed(RANDOM_STATE)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, generator=loader_generator
    )

    X_es_t = torch.from_numpy(X_earlystop)
    y_es_t = torch.from_numpy(y_earlystop)

    best_loss = float("inf")
    best_state = None
    best_epoch = 0
    epochs_without_improvement = 0
    history: list[float] = []

    for epoch in range(max_epochs):
        model.train()
        for xb, yb in train_loader:
            optimizer.zero_grad()
            pred = model(xb).squeeze(-1)
            loss = loss_fn(pred, yb)
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            es_pred = model(X_es_t).squeeze(-1)
            es_loss = loss_fn(es_pred, y_es_t).item()
        history.append(es_loss)

        if es_loss < best_loss - 1e-8:
            best_loss = es_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                break

    model.load_state_dict(best_state)
    return model, best_epoch, best_loss, history


def select_lookback(
    frame: pl.DataFrame,
    feature_cols: list[str],
    target_col: str,
    model_factory_for_input_size,
    lookback_candidates: list[int] = LOOKBACK_CANDIDATES,
) -> TrainResult:
    """Grid search over lookback_candidates, selected by early-stopping loss
    (never by val — val is reserved for the final, single evaluation).

    Args:
        frame: Output of prepare_frame.
        feature_cols: Predictor column names (defines input_size).
        target_col: Target column name.
        model_factory_for_input_size: Callable(input_size) -> nn.Module,
            e.g. `lambda n: LSTMRegressor(input_size=n)`.
        lookback_candidates: Lookback lengths to try.

    Returns:
        TrainResult for the winning lookback.
    """
    best: TrainResult | None = None
    for lookback in lookback_candidates:
        seqs = build_sequences(frame, feature_cols, target_col, lookback)
        fit_seq, earlystop_seq = chronological_earlystop_split(seqs["train"])
        scaler, (X_fit, X_earlystop) = scale_sequences(fit_seq.X, earlystop_seq.X)

        model, best_epoch, earlystop_loss, history = train_with_early_stopping(
            lambda: model_factory_for_input_size(len(feature_cols)),
            X_fit,
            fit_seq.y,
            X_earlystop,
            earlystop_seq.y,
        )
        logger.info(
            f"[deep_learning.select_lookback] lookback={lookback} "
            f"best_epoch={best_epoch} earlystop_loss={earlystop_loss:.6f}"
        )

        if best is None or earlystop_loss < best.earlystop_loss:
            best = TrainResult(
                model=model,
                scaler=scaler,
                lookback=lookback,
                best_epoch=best_epoch,
                earlystop_loss=earlystop_loss,
                history=history,
            )

    return best


def evaluate(
    result: TrainResult,
    frame: pl.DataFrame,
    feature_cols: list[str],
    target_col: str,
    split: str = "val",
):
    """Evaluate a trained TrainResult on one split, rebuilding sequences at
    the winning lookback and applying the winning scaler (fit on train only).

    Returns:
        (rmse, mae, dates, y_true, y_pred)
    """
    seqs = build_sequences(frame, feature_cols, target_col, result.lookback)
    seq = seqs[split]
    n_features = len(feature_cols)
    X_scaled = result.scaler.transform(seq.X.reshape(-1, n_features)).reshape(seq.X.shape)
    X_scaled = X_scaled.astype(np.float32)

    result.model.eval()
    with torch.no_grad():
        y_pred = result.model(torch.from_numpy(X_scaled)).squeeze(-1).numpy()

    rmse = float(np.sqrt(np.mean((seq.y - y_pred) ** 2)))
    mae = float(np.mean(np.abs(seq.y - y_pred)))
    return rmse, mae, seq.dates, seq.y, y_pred
