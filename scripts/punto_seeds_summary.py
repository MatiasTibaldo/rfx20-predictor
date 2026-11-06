"""
Consolida la prueba multi-semilla (seed=42 oficial + 7/123/2024/555 nuevas)
de la batería completa de Bloque 2 sobre el dataset baseline.

Uso: uv run python scripts/punto_seeds_summary.py
"""

from __future__ import annotations

import numpy as np
import polars as pl

from config.settings import settings

HORIZONS = [1, 3, 5]
SEEDS = [42, 7, 123, 2024, 555]

ML_MODELS = ["rf", "svm", "xgboost", "lightgbm"]
DL_MODELS = ["lstm", "gru", "cnn_lstm", "tft_lite"]
DISPLAY_NAME = {
    "rf": "RF", "svm": "SVM", "xgboost": "XGBoost", "lightgbm": "LightGBM",
    "lstm": "LSTM", "gru": "GRU", "cnn_lstm": "CNN-LSTM", "tft_lite": "Transformer encoder",
}


def path_for(seed: int, model: str, h: int) -> str:
    if seed == 42:
        if model in ML_MODELS:
            return f"results/track_a_ml/{model}/{model}_val_predictions_h{h}.parquet"
        return f"results/track_b/{model}_val_predictions_h{h}.parquet"
    kind = "ml" if model in ML_MODELS else "dl"
    sub = f"{model}/" if model in ML_MODELS else ""
    return f"results/punto_seeds/seed{seed}/{kind}/{sub}{model}_val_predictions_h{h}.parquet"


def pct_vs_naive(path: str) -> float:
    df = pl.read_parquet(path)
    yt, yp = df["y_true"].to_numpy(), df["y_pred"].to_numpy()
    mask = ~np.isnan(yt) & ~np.isnan(yp)
    yt, yp = yt[mask], yp[mask]
    rmse_model = np.sqrt(np.mean((yt - yp) ** 2))
    rmse_naive = np.sqrt(np.mean(yt**2))
    return (rmse_model / rmse_naive - 1.0) * 100


def main() -> None:
    rows = []
    for model in ML_MODELS + DL_MODELS:
        for h in HORIZONS:
            pcts = []
            for seed in SEEDS:
                p = path_for(seed, model, h)
                pcts.append(pct_vs_naive(p))
            arr = np.array(pcts)
            rows.append(
                {
                    "model": DISPLAY_NAME[model],
                    "horizon": h,
                    "seed42_oficial": pcts[0],
                    "mean": arr.mean(),
                    "std": arr.std(),
                    "min": arr.min(),
                    "max": arr.max(),
                    "all_same_sign": bool((arr > 0).all() or (arr < 0).all()),
                }
            )

    out = pl.DataFrame(rows)
    out.write_parquet(settings.RESULTS_DIR / "punto_seeds" / "summary.parquet")

    print(f"{'Modelo':<22}{'h':<4}{'seed42':<10}{'media':<10}{'std':<9}{'min':<10}{'max':<10}{'mismo signo'}")
    for row in rows:
        print(
            f"{row['model']:<22}{row['horizon']:<4}{row['seed42_oficial']:<+10.2f}"
            f"{row['mean']:<+10.2f}{row['std']:<9.2f}{row['min']:<+10.2f}{row['max']:<+10.2f}"
            f"{row['all_same_sign']}"
        )


if __name__ == "__main__":
    main()
