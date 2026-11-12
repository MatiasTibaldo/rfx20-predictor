"""
Punto 7 del feedback de los directores: un RMSE similar al naive no demuestra
ausencia de capacidad para anticipar el signo del retorno — esa dimensión
requiere su propia métrica. Calcula el hit-rate (% de aciertos de signo) de
los 9 modelos de dirección de Bloque 2, sobre las predicciones ya
persistidas de la re-corrida del Punto 3 (target acumulado, purga de borde),
con un test binomial contra 50% para cada (modelo, horizonte).

Agrega (seguimiento del director, 6-nov-2026) un benchmark adicional:
"mayoría de train" — predecir siempre el signo más frecuente del retorno
acumulado en train, por horizonte (el balance de subas/bajas puede variar
por horizonte, así que 50% no es necesariamente la referencia más justa).
Calculado sobre train para no filtrar información de val hacia la regla.

Uso: uv run python scripts/punto7_hitrate.py
"""

from __future__ import annotations

import numpy as np
import polars as pl
from scipy import stats

from config.settings import settings

HORIZONS = [1, 3, 5]

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


def hitrate(path: str, horizon_filter: int | None) -> dict:
    df = pl.read_parquet(path)
    if horizon_filter is not None:
        df = df.filter(pl.col("horizon") == horizon_filter)
    yt = df["y_true"].to_numpy()
    yp = df["y_pred"].to_numpy()
    mask = ~np.isnan(yt) & ~np.isnan(yp)
    yt, yp = yt[mask], yp[mask]

    pred_sign = np.sign(yp)
    true_sign = np.sign(yt)
    n = len(yt)
    hits = int((pred_sign == true_sign).sum())
    hit_pct = hits / n * 100
    pct_pos_actual = float((true_sign > 0).mean() * 100)
    pval = stats.binomtest(hits, n, 0.5, alternative="two-sided").pvalue
    return {"n": n, "hits": hits, "hit_pct": hit_pct, "pct_pos_actual": pct_pos_actual, "p_value": pval}


def majority_train_baseline(h: int) -> dict:
    """Hit-rate on val of "always predict train's majority sign", horizon h."""
    df = pl.read_parquet("data/features/v1/features_long.parquet")
    target_col = f"log_return_fwd_{h}"

    train_y = df.filter(pl.col("split") == "train")[target_col].drop_nulls().to_numpy()
    train_pct_pos = float((train_y > 0).mean() * 100)
    majority_sign = 1.0 if train_pct_pos >= 50.0 else -1.0

    val_y = df.filter(pl.col("split") == "val")[target_col].drop_nulls().to_numpy()
    true_sign = np.sign(val_y)
    n = len(val_y)
    hits = int((true_sign == majority_sign).sum())
    hit_pct = hits / n * 100
    pval = stats.binomtest(hits, n, 0.5, alternative="two-sided").pvalue
    return {
        "n": n,
        "hits": hits,
        "hit_pct": hit_pct,
        "pct_pos_actual": float((true_sign > 0).mean() * 100),
        "p_value": pval,
        "train_pct_pos": train_pct_pos,
        "majority_sign": "+" if majority_sign > 0 else "-",
    }


def main() -> None:
    rows = []
    for name, path_tpl, has_horizon_col in CONFIGS:
        for h in HORIZONS:
            path = path_tpl if has_horizon_col else path_tpl.format(h=h)
            r = hitrate(path, horizon_filter=h if has_horizon_col else None)
            rows.append({"model": name, "horizon": h, **r})

    print(f"\n{'Baseline':<18}{'h':<4}{'%pos train':<12}{'signo':<7}{'n':<6}{'hit%':<9}{'p-value'}")
    for h in HORIZONS:
        r = majority_train_baseline(h)
        print(
            f"{'Mayoría train':<18}{h:<4}{r['train_pct_pos']:<12.2f}{r['majority_sign']:<7}"
            f"{r['n']:<6}{r['hit_pct']:<9.2f}{r['p_value']:.4f}"
        )
        rows.append({"model": "Mayoría de train", "horizon": h, **{k: v for k, v in r.items() if k not in ("train_pct_pos", "majority_sign")}})
    print()

    out = pl.DataFrame(rows)
    results_dir = settings.RESULTS_DIR / "punto7_hitrate"
    results_dir.mkdir(parents=True, exist_ok=True)
    out.write_parquet(results_dir / "hitrate_summary.parquet")

    print(f"{'Modelo':<12}{'h':<4}{'n':<6}{'hit%':<9}{'%pos_real':<11}{'p-value':<10}")
    for row in rows:
        print(
            f"{row['model']:<12}{row['horizon']:<4}{row['n']:<6}{row['hit_pct']:<9.2f}"
            f"{row['pct_pos_actual']:<11.2f}{row['p_value']:<10.4f}"
        )

    n_significant = sum(1 for r in rows if r["p_value"] < 0.05)
    print(f"\n{n_significant}/{len(rows)} combinaciones (modelo, horizonte) con p < 0.05.")


if __name__ == "__main__":
    main()
