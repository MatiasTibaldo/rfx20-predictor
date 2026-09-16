"""EDA rapido: potencial predictivo de variables candidatas y efecto de outliers en log_return.

Exploratorio, no productivo: no persiste datos ni toca el pipeline de features.
Uso: uv run python scripts/eda_target_exploration.py
"""

import polars as pl

FEATURES_PATH = "data/features/v1/features_long.parquet"


def ac_lag1(x: pl.Series) -> float:
    """Autocorrelacion lag-1 simple (proxy rapido de memoria/persistencia de una serie)."""
    x = x.drop_nulls()
    if x.len() < 30:
        return float("nan")
    a, b = x[:-1], x[1:]
    return float(pl.DataFrame({"a": a, "b": b}).select(pl.corr("a", "b")).item())


def ar1_r2(x: pl.Series) -> float:
    """R^2 de un AR(1) (x_t ~ x_{t-1}) como proxy barato de predictibilidad."""
    r = ac_lag1(x)
    return r**2 if r == r else float("nan")


def describe_outliers(x: pl.Series, k: float = 1.5) -> dict:
    x = x.drop_nulls()
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - k * iqr, q3 + k * iqr
    n_out = x.filter((x < lo) | (x > hi)).len()
    return {"q1": q1, "q3": q3, "iqr": iqr, "lo": lo, "hi": hi, "n_out": n_out, "pct_out": n_out / x.len() * 100}


def skew_kurt(x: pl.Series) -> tuple[float, float]:
    x = x.drop_nulls()
    return float(x.skew()), float(x.kurtosis())


def main() -> None:
    df = pl.read_parquet(FEATURES_PATH).sort("date")

    print("=" * 70)
    print("1) Predictibilidad lag-1 (AR(1) R^2) por variable candidata")
    print("=" * 70)
    log_ret = df["log_return"]
    candidates = {
        "log_return": log_ret,
        "abs(log_return)": log_ret.abs(),
        "log_return^2": log_ret**2,
        "realized_vol_10": df["realized_vol_10"],
        "realized_vol_20": df["realized_vol_20"],
        "realized_vol_50": df["realized_vol_50"],
        "riesgo_pais": df["riesgo_pais"],
        "riesgo_pais_diff": df["riesgo_pais"].diff(),
        "tasa_pf": df["tasa_pf"],
        "tasa_pf_diff": df["tasa_pf"].diff(),
        "spread_oficial_informal": df["spread_oficial_informal"],
        "spread_oficial_informal_diff": df["spread_oficial_informal"].diff(),
        "term_spread_futures": df["term_spread_futures"],
    }
    rows = []
    for name, series in candidates.items():
        r = ac_lag1(series)
        rows.append({"variable": name, "autocorr_lag1": round(r, 4), "ar1_r2": round(r**2, 4) if r == r else None})
    result = pl.DataFrame(rows).sort("ar1_r2", descending=True)
    print(result)

    print()
    print("=" * 70)
    print("2) Outliers en log_return (regla IQR 1.5x y 3x)")
    print("=" * 70)
    for k in (1.5, 3.0):
        stats = describe_outliers(log_ret, k=k)
        print(f"k={k}: bounds=({stats['lo']:.5f}, {stats['hi']:.5f})  n_out={stats['n_out']}  pct={stats['pct_out']:.2f}%")

    print()
    print("Fechas de outliers (k=3x IQR), ordenadas por magnitud:")
    stats3 = describe_outliers(log_ret, k=3.0)
    out_df = (
        df.select("date", "log_return")
        .filter((pl.col("log_return") < stats3["lo"]) | (pl.col("log_return") > stats3["hi"]))
        .with_columns(abs_ret=pl.col("log_return").abs())
        .sort("abs_ret", descending=True)
    )
    print(out_df.head(20))

    print()
    print("=" * 70)
    print("3) Skew/kurtosis de log_return: crudo vs winsorizado (1%/99%) vs sin outliers (3x IQR)")
    print("=" * 70)
    s_raw, k_raw = skew_kurt(log_ret)
    print(f"Crudo:        skew={s_raw:.3f}  kurtosis={k_raw:.3f}  n={log_ret.drop_nulls().len()}")

    p1, p99 = log_ret.quantile(0.01), log_ret.quantile(0.99)
    wins = log_ret.clip(p1, p99)
    s_w, k_w = skew_kurt(wins)
    print(f"Winsorizado:  skew={s_w:.3f}  kurtosis={k_w:.3f}  bounds=({p1:.5f}, {p99:.5f})")

    no_out = log_ret.filter((log_ret >= stats3["lo"]) & (log_ret <= stats3["hi"]))
    s_no, k_no = skew_kurt(no_out)
    print(f"Sin outliers: skew={s_no:.3f}  kurtosis={k_no:.3f}  n={no_out.len()} (se quitaron {log_ret.drop_nulls().len() - no_out.len()})")

    print()
    print("Rango crudo:        [{:.5f}, {:.5f}]".format(log_ret.min(), log_ret.max()))
    print("Rango sin outliers: [{:.5f}, {:.5f}]".format(no_out.min(), no_out.max()))

    print()
    print("=" * 70)
    print("4) Autocorrelacion lag1 de log_return con y sin outliers (3x IQR)")
    print("=" * 70)
    print(f"Con outliers:  r1={ac_lag1(log_ret):.4f}")
    print(f"Sin outliers:  r1={ac_lag1(no_out):.4f}")


if __name__ == "__main__":
    main()
