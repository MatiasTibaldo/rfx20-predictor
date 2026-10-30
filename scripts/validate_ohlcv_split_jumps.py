"""
Punto 1 del feedback de los directores: valida las series OHLCV crudas
(data/raw/v1/{ticker}_ohlcv.parquet) buscando saltos día-a-día compatibles
con un split, y los cruza contra lo ya documentado en
config/data_corrections.yaml (splits: y composition_only_splits:).

Objetivo: para cada ticker, determinar si el OHLCV en origen YA viene
split-adjusted (no debería verse el salto) o si viene nominal (el salto
debería verse crudo, y requiere SplitAdjuster) — y detectar cualquier salto
sin documentar.

Uso: uv run python scripts/validate_ohlcv_split_jumps.py
"""

from __future__ import annotations

import datetime

import polars as pl
import yaml

RAW_DIR = "data/raw/v1"
CONFIG_PATH = "config/data_corrections.yaml"

# ratio = close_t / close_{t-1}. Un split k:1 produce ratio ~ 1/k.
# 1.67 = 1/0.6, cubre splits desde ~1.67:1 en adelante en cualquier direccion.
JUMP_LOW, JUMP_HIGH = 0.6, 1.67


def load_tickers() -> list[str]:
    import glob

    return sorted(
        p.split("/")[-1].replace("_ohlcv.parquet", "").upper()
        for p in glob.glob(f"{RAW_DIR}/*_ohlcv.parquet")
    )


def load_documented_splits() -> list[dict]:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    events = []
    for entry in cfg.get("splits", []):
        events.append({
            "ticker": entry["ticker"], "date": entry["date"], "ratio": entry["ratio"],
            "registro": "splits (ajusta OHLCV via SplitAdjuster)",
        })
    for entry in cfg.get("composition_only_splits", []):
        events.append({
            "ticker": entry["ticker"], "date": entry["date"], "ratio": entry["ratio"],
            "registro": "composition_only_splits (OHLCV ya ajustado en origen, segun doc)",
        })
    return events


def find_jumps(ticker: str) -> pl.DataFrame:
    path = f"{RAW_DIR}/{ticker.lower()}_ohlcv.parquet"
    df = pl.read_parquet(path).sort("date")
    df = df.with_columns((pl.col("close") / pl.col("close").shift(1)).alias("ratio"))
    jumps = df.filter(
        pl.col("ratio").is_not_null() & ((pl.col("ratio") < JUMP_LOW) | (pl.col("ratio") > JUMP_HIGH))
    ).select("date", "close", "ratio")
    return jumps.with_columns(pl.lit(ticker).alias("ticker"))


def main() -> None:
    tickers = load_tickers()
    documented = load_documented_splits()
    print(f"{len(tickers)} tickers, {len(documented)} eventos documentados (splits + composition_only_splits)\n")

    all_jumps = []
    for t in tickers:
        j = find_jumps(t)
        if j.height:
            all_jumps.append(j)

    jumps_df = pl.concat(all_jumps) if all_jumps else pl.DataFrame()
    print(f"Total de saltos crudos detectados (ratio fuera de [{JUMP_LOW}, {JUMP_HIGH}]): {jumps_df.height}\n")

    def match_documented(ticker: str, date: datetime.date) -> dict | None:
        for ev in documented:
            ev_date = datetime.date.fromisoformat(ev["date"])
            if ev["ticker"] == ticker and abs((ev_date - date).days) <= 3:
                return ev
        return None

    matched_tickers_dates = set()
    print("=== Saltos crudos detectados, cruzados contra lo documentado ===\n")
    for row in jumps_df.sort(["ticker", "date"]).to_dicts():
        ev = match_documented(row["ticker"], row["date"])
        if ev:
            matched_tickers_dates.add((ev["ticker"], ev["date"]))
            tag = "OK (documentado)"
            detail = f"-> {ev['registro']} | ratio esperado ~{1/ev['ratio']:.4f}"
        else:
            tag = "** SIN DOCUMENTAR **"
            detail = ""
        print(f"  [{tag}] {row['ticker']:<8} {row['date']} ratio={row['ratio']:.4f} close={row['close']:.4f}  {detail}")

    print("\n=== Verificacion inversa: tickers de composition_only_splits (deberian NO mostrar salto crudo) ===\n")
    for ev in documented:
        if "composition_only_splits" not in ev["registro"]:
            continue
        key = (ev["ticker"], ev["date"])
        ev_date = datetime.date.fromisoformat(ev["date"])
        nearby = jumps_df.filter(
            (pl.col("ticker") == ev["ticker"])
            & (pl.col("date") >= ev_date - datetime.timedelta(days=3))
            & (pl.col("date") <= ev_date + datetime.timedelta(days=3))
        )
        status = "salto encontrado (inesperado)" if nearby.height else "sin salto (consistente con 'ya ajustado en origen')"
        print(f"  {ev['ticker']:<8} {ev['date']} (ratio doc={ev['ratio']}): {status}")

    print("\n=== Verificacion directa: tickers de 'splits:' (deberian SI mostrar salto crudo) ===\n")
    for ev in documented:
        if "splits (" not in ev["registro"]:
            continue
        key = (ev["ticker"], ev["date"])
        status = "OK, salto encontrado" if key in matched_tickers_dates else "** NO SE ENCONTRO EL SALTO ESPERADO **"
        print(f"  {ev['ticker']:<8} {ev['date']} (ratio doc={ev['ratio']}): {status}")


if __name__ == "__main__":
    main()
