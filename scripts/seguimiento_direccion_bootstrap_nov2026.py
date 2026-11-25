"""
Feedback de seguimiento de los directores (6-nov-2026), sobre la sección
5.4.1 de la tesis: el test binomial vs. 50% no es la comparación más
relevante, ya que el propio documento ya identificó "mayoría de train"
(predecir siempre el signo más frecuente del retorno acumulado en train)
como el benchmark que de verdad importa superar. El director pidió aplicar
el bootstrap de bloques — ya usado para RMSE en el Punto 9
(`scripts/punto9_bootstrap_ci.py`) — a la diferencia de aciertos entre cada
modelo y esa regla, sobre las mismas fechas, en vez de apoyarse solo en el
test binomial.

Para cada (modelo, horizonte), calcula el vector diario de aciertos de
signo del modelo y el de la regla "mayoría de train" sobre las mismas
fechas de validación, y un intervalo de confianza 95% por block bootstrap
(mismo L=10, B=2000, semilla 42 que el Punto 9) para la diferencia media
de aciertos (`hit_modelo - hit_mayoria`). La diferencia media de un vector
0/1 es exactamente la diferencia de hit-rate, así que el bootstrap aplica
sin transformación adicional.

Uso: uv run python scripts/seguimiento_direccion_bootstrap_nov2026.py
"""

from __future__ import annotations

import numpy as np
import polars as pl

from config.settings import settings

HORIZONS = [1, 3, 5]
BLOCK_LENGTH = 10
N_BOOT = 2000
RNG_SEED = 42

CONFIGS = [
    ("ARIMA/SARIMA", "results/track_a/arima_val_predictions.parquet", True),
    ("SVM", "results/track_a_ml/svm/svm_val_predictions_h{h}.parquet", False),
    ("Random Forest", "results/track_a_ml/rf/rf_val_predictions_h{h}.parquet", False),
    ("XGBoost", "results/track_a_ml/xgboost/xgboost_val_predictions_h{h}.parquet", False),
    ("LightGBM", "results/track_a_ml/lightgbm/lightgbm_val_predictions_h{h}.parquet", False),
    ("LSTM", "results/track_b/lstm_val_predictions_h{h}.parquet", False),
    ("GRU", "results/track_b/gru_val_predictions_h{h}.parquet", False),
    ("CNN-LSTM", "results/track_b/cnn_lstm_val_predictions_h{h}.parquet", False),
    ("Transformer encoder", "results/track_b/tft_lite_val_predictions_h{h}.parquet", False),
]


def majority_train_sign(h: int) -> float:
    df = pl.read_parquet("data/features/v1/features_long.parquet")
    train_y = df.filter(pl.col("split") == "train")[f"log_return_fwd_{h}"].drop_nulls().to_numpy()
    return 1.0 if (train_y > 0).mean() >= 0.5 else -1.0


def load_hits(path: str, horizon_filter: int | None, majority_sign: float) -> tuple[np.ndarray, np.ndarray]:
    """Returns (hit_model, hit_majority) arrays, aligned by date, sorted chronologically."""
    df = pl.read_parquet(path).sort("date")
    if horizon_filter is not None:
        df = df.filter(pl.col("horizon") == horizon_filter)
    yt = df["y_true"].to_numpy()
    yp = df["y_pred"].to_numpy()
    mask = ~np.isnan(yt) & ~np.isnan(yp)
    yt, yp = yt[mask], yp[mask]
    true_sign = np.sign(yt)
    hit_model = (np.sign(yp) == true_sign).astype(float)
    hit_majority = (true_sign == majority_sign).astype(float)
    return hit_model, hit_majority


def block_bootstrap_ci_diff(
    hit_model: np.ndarray, hit_majority: np.ndarray, block_length: int, n_boot: int, rng: np.random.Generator
) -> tuple[float, float]:
    """Moving block bootstrap CI (95%) for the mean difference (hit_model - hit_majority)."""
    n = len(hit_model)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    diff = hit_model - hit_majority
    samples = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        samples[b] = diff[idx].mean()
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for name, path_tpl, has_horizon_col in CONFIGS:
        for h in HORIZONS:
            path = path_tpl if has_horizon_col else path_tpl.format(h=h)
            majority_sign = majority_train_sign(h)
            hit_model, hit_majority = load_hits(path, horizon_filter=h if has_horizon_col else None, majority_sign=majority_sign)
            n = len(hit_model)
            hitrate_model = float(hit_model.mean() * 100)
            hitrate_majority = float(hit_majority.mean() * 100)
            diff_pp = hitrate_model - hitrate_majority
            ci_lo, ci_hi = block_bootstrap_ci_diff(hit_model, hit_majority, BLOCK_LENGTH, N_BOOT, rng)
            rows.append(
                {
                    "model": name,
                    "horizon": h,
                    "n": n,
                    "hitrate_model": hitrate_model,
                    "hitrate_majority": hitrate_majority,
                    "diff_pp": diff_pp,
                    "ci95_lo_pp": ci_lo * 100,
                    "ci95_hi_pp": ci_hi * 100,
                    "excludes_zero": (ci_lo > 0) or (ci_hi < 0),
                }
            )

    out = pl.DataFrame(rows)
    results_dir = settings.RESULTS_DIR / "seguimiento_direccion_bootstrap"
    results_dir.mkdir(parents=True, exist_ok=True)
    out.write_parquet(results_dir / "direccion_bootstrap_summary.parquet")

    print(f"{'Modelo':<20}{'h':<4}{'hit% modelo':<13}{'hit% mayoría':<14}{'dif. pp':<10}{'CI95% (pp)':<22}{'excl.0'}")
    for row in rows:
        ci_str = f"[{row['ci95_lo_pp']:+.2f}, {row['ci95_hi_pp']:+.2f}]"
        print(
            f"{row['model']:<20}{row['horizon']:<4}{row['hitrate_model']:<13.2f}{row['hitrate_majority']:<14.2f}"
            f"{row['diff_pp']:<+10.2f}{ci_str:<22}{row['excludes_zero']}"
        )

    n_excl = sum(1 for r in rows if r["excludes_zero"])
    print(f"\n{n_excl}/{len(rows)} combinaciones con IC 95% que excluye 0 (diferencia de hit-rate vs. "
          f"'mayoría de train' no compatible con variabilidad muestral pura, bootstrap de bloques, L={BLOCK_LENGTH}).")


if __name__ == "__main__":
    main()
