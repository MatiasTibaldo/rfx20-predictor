"""
Punto 6 del feedback de los directores: auditoría de las degradaciones de
Deep Learning antes de atribuirlas únicamente a sobreajuste.

Para un puñado de configuraciones representativas (las más degradadas y una
de contraste que se comporta bien), con el lookback YA seleccionado por la
corrida oficial (no se vuelve a buscar acá, para no mezclar varianza de
selección de lookback con varianza de semilla):

1. Persiste la curva de pérdida de early stopping (antes se calculaba y se
   descartaba).
2. Repite el entrenamiento con 3 semillas distintas para medir estabilidad.

Uso: uv run python scripts/punto6_dl_diagnostics.py
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl
import torch

from config.settings import settings
from models.deep_learning import common as dl_common
from models.deep_learning.cnn_lstm import CNNLSTMRegressor
from models.deep_learning.common import (
    FEATURE_SET_FULL,
    build_sequences,
    chronological_earlystop_split,
    prepare_frame,
    purge_train_tail,
    scale_sequences,
)
from models.deep_learning.gru import GRURegressor
from models.deep_learning.lstm import LSTMRegressor
from storage.store import DuckDBStore

RESULTS_DIR = settings.RESULTS_DIR / "punto6_dl_diagnostics"

# (label, dataset_name, model_cls, kwargs, horizon, lookback — ya elegido por la corrida oficial)
CONFIGS = [
    ("GRU-compA-h5", "features_long_compA", GRURegressor, {"hidden_size": 32}, 5, 10),
    ("LSTM-compC_masked-h5", "features_long_compC_masked", LSTMRegressor, {"hidden_size": 32}, 5, 10),
    ("CNN-LSTM-compA-h1 (contraste)", "features_long_compA", CNNLSTMRegressor, {"hidden_size": 32}, 1, 30),
]

SEEDS = [42, 7, 123]


def run_one(label, dataset_name, model_cls, model_kwargs, horizon, lookback, seed):
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name=dataset_name, version="v1")
    frame, feature_cols, target_col = prepare_frame(df, horizon=horizon, feature_set=FEATURE_SET_FULL)

    seqs = build_sequences(frame, feature_cols, target_col, lookback)
    seqs = purge_train_tail(seqs, horizon)
    fit_seq, earlystop_seq = chronological_earlystop_split(seqs["train"])
    scaler, (X_fit, X_earlystop) = scale_sequences(fit_seq.X, earlystop_seq.X)

    dl_common.RANDOM_STATE = seed  # monkeypatch: train_with_early_stopping reads the module global
    model, best_epoch, earlystop_loss, history = dl_common.train_with_early_stopping(
        lambda: model_cls(input_size=len(feature_cols), **model_kwargs),
        X_fit,
        fit_seq.y,
        X_earlystop,
        earlystop_seq.y,
    )

    val_seq = seqs["val"]
    n_features = len(feature_cols)
    X_val_scaled = scaler.transform(val_seq.X.reshape(-1, n_features)).reshape(val_seq.X.shape).astype(np.float32)
    model.eval()
    with torch.no_grad():
        y_pred = model(torch.from_numpy(X_val_scaled)).squeeze(-1).numpy()
    y_true = val_seq.y
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    return {
        "label": label,
        "seed": seed,
        "best_epoch": best_epoch,
        "n_epochs_run": len(history),
        "earlystop_loss_first": history[0],
        "earlystop_loss_best": earlystop_loss,
        "earlystop_loss_last": history[-1],
        "val_rmse": rmse,
        "y_pred_mean": float(y_pred.mean()),
        "y_pred_std": float(y_pred.std()),
        "history": history,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for label, dataset_name, model_cls, model_kwargs, horizon, lookback in CONFIGS:
        print(f"\n=== {label} (lookback={lookback}, horizon={horizon}) ===")
        for seed in SEEDS:
            r = run_one(label, dataset_name, model_cls, model_kwargs, horizon, lookback, seed)
            all_rows.append(r)
            print(
                f"  seed={seed}: best_epoch={r['best_epoch']}/{r['n_epochs_run']} "
                f"earlystop_loss {r['earlystop_loss_first']:.5f} -> {r['earlystop_loss_best']:.5f} "
                f"(last={r['earlystop_loss_last']:.5f})  val_rmse={r['val_rmse']:.5f}  "
                f"y_pred(mean={r['y_pred_mean']:+.4f}, std={r['y_pred_std']:.4f})"
            )

    with open(RESULTS_DIR / "seed_stability.json", "w") as f:
        json.dump(all_rows, f, indent=2)

    print("\n\n===== RESUMEN: estabilidad entre semillas (val_rmse) =====")
    by_label: dict[str, list[float]] = {}
    for r in all_rows:
        by_label.setdefault(r["label"], []).append(r["val_rmse"])
    for label, rmses in by_label.items():
        arr = np.array(rmses)
        print(f"{label:35s} rmse por semilla={[f'{x:.5f}' for x in rmses]}  "
              f"mean={arr.mean():.5f}  std={arr.std():.5f}  cv={arr.std()/arr.mean()*100:.1f}%")


if __name__ == "__main__":
    main()
