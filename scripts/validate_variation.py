import argparse
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd


def read_parquet_file(file_path: Path) -> list[dict]:
    """Read a parquet file, return rows as dicts: instrument, open, close, date."""
    try:
        df = pd.read_parquet(file_path)
    except Exception:
        return []

    required = {"ticker", "close", "date"}
    if not required.issubset(df.columns):
        return []

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    rows = []
    for _, row in df.iterrows():
        if pd.isna(row["ticker"]) or pd.isna(row["date"]) or pd.isna(row["close"]):
            continue
        close_val = float(row["close"])
        open_val = (
            float(row["open"])
            if "open" in df.columns and not pd.isna(row["open"])
            else close_val
        )
        if close_val == 0 or open_val == 0:
            print(
                f"  [WARN] Precio cero en {file_path.name} "
                f"({row['ticker']} {row['date'].date()}) — fila ignorada"
            )
            continue
        rows.append(
            {
                "instrument": str(row["ticker"]).strip().upper(),
                "open": open_val,
                "close": close_val,
                "date": row["date"],
            }
        )
    return rows


def _ratio(prev_close: float, open_next: float, variation: float) -> float:
    """Ratio implícito del evento: >1 siempre, indica magnitud del salto."""
    if variation < 0:
        return round(prev_close / open_next, 4) if open_next != 0 else math.nan
    else:
        return round(open_next / prev_close, 4) if prev_close != 0 else math.nan


def detect_variations(rows: list[dict], threshold: float = 30.0) -> list[dict]:
    """Detecta variaciones overnight > threshold usando días hábiles consecutivos.

    Compara la posición i con i-1 en la lista ordenada de fechas reales
    de cada instrumento — sin restricción de gap calendario.

    Returns:
        Lista de dicts: instrument, date, date_str, tipo, variacion_pct,
                        ratio_implicito, prev_close, open_next, context.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[r["instrument"]].append(r)

    alerts = []
    for instrument, items in sorted(grouped.items()):
        items.sort(key=lambda x: x["date"])
        n = len(items)
        for i in range(1, n):
            prev = items[i - 1]
            curr = items[i]
            prev_close = prev["close"]
            open_next = curr["open"]

            if prev_close == 0 or open_next == 0:
                continue

            variation = (open_next - prev_close) / prev_close * 100
            if abs(variation) <= threshold:
                continue

            tipo = "split_candidato" if variation < 0 else "split_inverso_candidato"
            ratio = _ratio(prev_close, open_next, variation)

            # Ventana de contexto ±3 días hábiles
            ctx_start = max(0, i - 3)
            ctx_end = min(n - 1, i + 3)
            context = []
            for j in range(ctx_start, ctx_end + 1):
                it = items[j]
                if j == 0:
                    var_dia = None
                else:
                    prev_c = items[j - 1]["close"]
                    var_dia = (
                        round((it["close"] - prev_c) / prev_c * 100, 2)
                        if prev_c != 0
                        else None
                    )
                context.append(
                    {
                        "fecha": it["date"].strftime("%d/%m/%Y"),
                        "open": it["open"],
                        "close": it["close"],
                        "var_dia_pct": var_dia,
                        "is_event": (j == i),
                    }
                )

            alerts.append(
                {
                    "instrument": instrument,
                    "date": curr["date"],
                    "date_str": curr["date"].strftime("%d/%m/%Y"),
                    "tipo": tipo,
                    "variacion_pct": round(variation, 2),
                    "ratio_implicito": ratio,
                    "prev_close": prev_close,
                    "open_next": open_next,
                    "context": context,
                }
            )

    return alerts


def load_composition_index(parquet_path: Path) -> set[tuple[str, str]]:
    """Carga composición del índice, devuelve conjunto (ticker_upper, 'YYYY-MM-DD')."""
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        print(f"  [WARN] No se pudo leer composición: {e}")
        return set()

    if not {"ticker", "date"}.issubset(df.columns):
        print("  [WARN] El parquet de composición no tiene columnas 'ticker' / 'date'")
        return set()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    index_set: set[tuple[str, str]] = set()
    for _, row in df.iterrows():
        if pd.isna(row["ticker"]) or pd.isna(row["date"]):
            continue
        index_set.add((str(row["ticker"]).strip().upper(), row["date"].strftime("%Y-%m-%d")))
    return index_set


def _ticker_in_index(ticker: str, date: pd.Timestamp, index_set: set) -> bool:
    return (ticker.upper(), date.strftime("%Y-%m-%d")) in index_set


def _print_alert(alert: dict, en_indice: str | None) -> None:
    sep = "=" * 64
    print(sep)
    label = (
        "SPLIT CANDIDATO        (precio bajó)"
        if alert["tipo"] == "split_candidato"
        else "SPLIT INVERSO CANDIDATO (precio subió)"
    )
    print(f"  {alert['instrument']}  —  {alert['date_str']}  —  {label}")
    print(
        f"  Variación overnight : {alert['variacion_pct']:+.2f}%"
        f"  |  prev_close={alert['prev_close']:.4f}  open={alert['open_next']:.4f}"
    )
    print(f"  Ratio implícito     : {alert['ratio_implicito']:.4f}:1")
    if en_indice is not None:
        print(f"  En índice           : {en_indice}")
    print()
    print(f"  {'Fecha':<12}  {'Open':>10}  {'Close':>10}  {'Var día %':>10}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}")
    for ctx_row in alert["context"]:
        marker = "  <-- EVENTO" if ctx_row["is_event"] else ""
        var_str = (
            f"{ctx_row['var_dia_pct']:+.2f}" if ctx_row["var_dia_pct"] is not None else "—"
        )
        print(
            f"  {ctx_row['fecha']:<12}  {ctx_row['open']:>10.4f}"
            f"  {ctx_row['close']:>10.4f}  {var_str:>10}{marker}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detecta variaciones abruptas overnight (candidatos a splits) en datos OHLCV"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "data" / "raw" / "v1"),
        help="Directorio con archivos *_ohlcv.parquet (default: ../data/raw/v1)",
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        default=None,
        help="CSV alternativo con columnas date,open,high,low,close,volume,ticker",
    )
    parser.add_argument(
        "--instrument",
        type=str,
        default=None,
        help="Filtrar por ticker específico",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=30.0,
        help="Umbral de variación en %% para generar alerta (default: 30)",
    )
    parser.add_argument(
        "--composition-parquet",
        type=str,
        default=None,
        help="Path al rfx20_composition.parquet para etiquetar si el ticker estaba en el índice",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Exportar reporte completo a este archivo CSV",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"Error: {data_dir} no es un directorio válido")
        return

    # --- Cargar datos ---
    all_rows: list[dict] = []
    parquet_files = sorted(data_dir.rglob("*_ohlcv.parquet"))
    print(f"Archivos parquet encontrados: {len(parquet_files)}  ({data_dir})")

    for pf in parquet_files:
        # Exportar CSV lateral para inspección manual
        try:
            pd.read_parquet(pf).to_csv(pf.with_suffix(".csv"), index=False)
        except Exception:
            pass
        all_rows.extend(read_parquet_file(pf))

    # CSV opcional como fuente adicional
    if args.csv_file:
        csv_path = Path(args.csv_file)
        if csv_path.is_file():
            try:
                df_csv = pd.read_csv(csv_path)
                for _, row in df_csv.iterrows():
                    if any(
                        pd.isna(row.get(c))
                        for c in ("date", "open", "close", "ticker")
                    ):
                        continue
                    try:
                        date_val = pd.to_datetime(row["date"], dayfirst=False)
                    except Exception:
                        continue
                    open_val, close_val = float(row["open"]), float(row["close"])
                    if open_val == 0 or close_val == 0:
                        print(
                            f"  [WARN] Precio cero en CSV "
                            f"({row['ticker']} {row['date']}) — fila ignorada"
                        )
                        continue
                    all_rows.append(
                        {
                            "instrument": str(row["ticker"]).strip().upper(),
                            "open": open_val,
                            "close": close_val,
                            "date": date_val,
                        }
                    )
            except Exception as e:
                print(f"  [WARN] No se pudo leer CSV {csv_path}: {e}")

    # Deduplicación: una entrada por (instrumento, fecha); priorizar open no-nulo
    deduped: dict[tuple, dict] = {}
    for r in all_rows:
        key = (r["instrument"], r["date"])
        if key not in deduped:
            deduped[key] = r
        elif pd.isna(deduped[key]["open"]) and not pd.isna(r["open"]):
            deduped[key] = r
    all_rows = list(deduped.values())

    total_rows = len(all_rows)
    print(f"Total filas (post-dedup)  : {total_rows}")

    # Filtro por instrumento
    if args.instrument:
        ticker_filter = args.instrument.upper()
        all_rows = [r for r in all_rows if r["instrument"] == ticker_filter]
        print(f"Filtrado por instrumento  : {ticker_filter} ({len(all_rows)} filas)")

    unique_instruments = {r["instrument"] for r in all_rows}
    unique_dates = {r["date"] for r in all_rows}

    # --- Detectar variaciones ---
    print(f"\nAnalizando variaciones overnight > {args.threshold:.0f}% …\n")
    alerts = detect_variations(all_rows, threshold=args.threshold)

    # --- Composición del índice ---
    index_set: set = set()
    use_composition = False
    if args.composition_parquet:
        comp_path = Path(args.composition_parquet)
        # Si el path no existe tal cual, intentar relativo a la raíz del proyecto
        if not comp_path.is_file():
            project_root = Path(__file__).resolve().parents[1]
            comp_path = project_root / args.composition_parquet
        if comp_path.is_file():
            print(f"Composición del índice: {comp_path.resolve()}\n")
            index_set = load_composition_index(comp_path)
            use_composition = True
        else:
            print(f"  [WARN] --composition-parquet no encontrado: {comp_path.resolve()}")

    # --- Resultados ---
    if not alerts:
        print(
            f"No se encontraron variaciones > {args.threshold:.0f}%.\n"
            f"  Instrumentos analizados : {len(unique_instruments)}\n"
            f"  Fechas distintas        : {len(unique_dates)}"
        )
        return

    print(f"Variaciones > {args.threshold:.0f}% detectadas: {len(alerts)}\n")

    in_index_count = 0
    out_index_count = 0
    report_rows = []

    for alert in alerts:
        en_indice: str | None = None
        if use_composition:
            in_idx = _ticker_in_index(alert["instrument"], alert["date"], index_set)
            en_indice = "Sí" if in_idx else "No"
            if in_idx:
                in_index_count += 1
            else:
                out_index_count += 1

        _print_alert(alert, en_indice)

        report_rows.append(
            {
                "ticker": alert["instrument"],
                "fecha": alert["date_str"],
                "tipo": alert["tipo"],
                "variacion_pct": alert["variacion_pct"],
                "ratio_implicito": alert["ratio_implicito"],
                "en_indice": en_indice if use_composition else "",
            }
        )

    # Resumen final
    print("=" * 64)
    print(f"Total alertas            : {len(alerts)}")
    print(f"  split_candidato        : {sum(1 for a in alerts if a['tipo'] == 'split_candidato')}")
    print(f"  split_inverso_candidato: {sum(1 for a in alerts if a['tipo'] == 'split_inverso_candidato')}")
    if use_composition:
        print(f"\nDentro del período de participación en el índice : {in_index_count}")
        print(f"Fuera del período de participación               : {out_index_count}")

    # Exportar CSV
    if args.output_csv:
        out_path = Path(args.output_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(report_rows).to_csv(out_path, index=False)
        print(f"\nReporte exportado: {out_path}")


if __name__ == "__main__":
    main()
