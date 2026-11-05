"""
Punto 9 del feedback de los directores: medida de incertidumbre para las
diferencias pequeñas (<0,4%) frente al naive. Para cada (modelo, horizonte)
de los 9 modelos de dirección, calcula:

- RMSE y MAE absolutos, N (ya se reportaban en los documentos, se repiten acá
  para tenerlos junto al intervalo).
- Intervalo de confianza 95% por block bootstrap (bloques móviles, preserva
  la dependencia temporal y la superposición entre horizontes) para la
  diferencia % de RMSE vs. naive.
- Apertura temporal: RMSE por mitad cronológica de val, para detectar si el
  resultado depende de un tramo acotado de jornadas.

Block bootstrap, no bootstrap i.i.d.: los errores de pronóstico a h días se
solapan entre fechas consecutivas (el target de hoy y el de mañana comparten
h-1 retornos diarios), lo que induce autocorrelación tipo MA(h-1) incluso si
el modelo no tiene memoria — un bootstrap i.i.d. subestimaría el error
estándar. Longitud de bloque fija en 10 (jornadas), igual para los 3
horizontes, por simplicidad y para no sobre-ajustar un parámetro sin
justificación adicional.

Uso: uv run python scripts/punto9_bootstrap_ci.py
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
    ("ARIMA", "results/track_a/arima_val_predictions.parquet", True),
    ("SVM", "results/track_a_ml/svm/svm_val_predictions_h{h}.parquet", False),
    ("RF", "results/track_a_ml/rf/rf_val_predictions_h{h}.parquet", False),
    ("XGBoost", "results/track_a_ml/xgboost/xgboost_val_predictions_h{h}.parquet", False),
    ("LightGBM", "results/track_a_ml/lightgbm/lightgbm_val_predictions_h{h}.parquet", False),
    ("LSTM", "results/track_b/lstm_val_predictions_h{h}.parquet", False),
    ("GRU", "results/track_b/gru_val_predictions_h{h}.parquet", False),
    ("CNN-LSTM", "results/track_b/cnn_lstm_val_predictions_h{h}.parquet", False),
    ("TFT-lite", "results/track_b/tft_lite_val_predictions_h{h}.parquet", False),
]


def load_series(path: str, horizon_filter: int | None) -> tuple[np.ndarray, np.ndarray]:
    df = pl.read_parquet(path).sort("date")
    if horizon_filter is not None:
        df = df.filter(pl.col("horizon") == horizon_filter)
    yt = df["y_true"].to_numpy()
    yp = df["y_pred"].to_numpy()
    mask = ~np.isnan(yt) & ~np.isnan(yp)
    return yt[mask], yp[mask]


def pct_vs_naive(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    rmse_model = np.sqrt(np.mean((y_true - y_pred) ** 2))
    rmse_naive = np.sqrt(np.mean(y_true**2))
    return (rmse_model / rmse_naive - 1.0) * 100


def block_bootstrap_ci(
    y_true: np.ndarray, y_pred: np.ndarray, block_length: int, n_boot: int, rng: np.random.Generator
) -> tuple[float, float]:
    """Moving block bootstrap CI (95%) for the % RMSE difference vs. naive."""
    n = len(y_true)
    n_blocks = int(np.ceil(n / block_length))
    max_start = n - block_length
    samples = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        samples[b] = pct_vs_naive(y_true[idx], y_pred[idx])
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def temporal_split_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    """RMSE on the chronological first half vs. second half of the series."""
    mid = len(y_true) // 2
    rmse_1 = np.sqrt(np.mean((y_true[:mid] - y_pred[:mid]) ** 2))
    rmse_2 = np.sqrt(np.mean((y_true[mid:] - y_pred[mid:]) ** 2))
    return float(rmse_1), float(rmse_2)


def main() -> None:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for name, path_tpl, has_horizon_col in CONFIGS:
        for h in HORIZONS:
            path = path_tpl if has_horizon_col else path_tpl.format(h=h)
            y_true, y_pred = load_series(path, horizon_filter=h if has_horizon_col else None)
            n = len(y_true)
            rmse_model = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            mae_model = float(np.mean(np.abs(y_true - y_pred)))
            rmse_naive = float(np.sqrt(np.mean(y_true**2)))
            pct = pct_vs_naive(y_true, y_pred)
            ci_lo, ci_hi = block_bootstrap_ci(y_true, y_pred, BLOCK_LENGTH, N_BOOT, rng)
            rmse_h1, rmse_h2 = temporal_split_rmse(y_true, y_pred)
            rows.append(
                {
                    "model": name,
                    "horizon": h,
                    "n": n,
                    "rmse": rmse_model,
                    "mae": mae_model,
                    "rmse_naive": rmse_naive,
                    "pct_vs_naive": pct,
                    "ci95_lo": ci_lo,
                    "ci95_hi": ci_hi,
                    "excludes_zero": (ci_lo > 0) or (ci_hi < 0),
                    "rmse_first_half": rmse_h1,
                    "rmse_second_half": rmse_h2,
                }
            )

    out = pl.DataFrame(rows)
    results_dir = settings.RESULTS_DIR / "punto9_bootstrap"
    results_dir.mkdir(parents=True, exist_ok=True)
    out.write_parquet(results_dir / "bootstrap_ci_summary.parquet")

    print(f"{'Modelo':<10}{'h':<4}{'RMSE':<10}{'MAE':<10}{'% vs naive':<12}{'CI95%':<20}{'excl.0':<8}{'1ra mitad':<11}{'2da mitad':<11}")
    for row in rows:
        ci_str = f"[{row['ci95_lo']:+.2f}, {row['ci95_hi']:+.2f}]"
        print(
            f"{row['model']:<10}{row['horizon']:<4}{row['rmse']:<10.5f}{row['mae']:<10.5f}"
            f"{row['pct_vs_naive']:<+12.2f}{ci_str:<20}{str(row['excludes_zero']):<8}"
            f"{row['rmse_first_half']:<11.5f}{row['rmse_second_half']:<11.5f}"
        )

    n_excl = sum(1 for r in rows if r["excludes_zero"])
    print(f"\n{n_excl}/{len(rows)} combinaciones con IC 95% que excluye 0 (diferencia vs. naive "
          f"no compatible con variabilidad muestral pura, bootstrap de bloques, L={BLOCK_LENGTH}).")


if __name__ == "__main__":
    main()
