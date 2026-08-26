"""
Backfill de composición RFX20 (Cartera Historica/Vigente/Proyectada + divisor)
con el WS de MatbaRofex, solo por esta vez — para cubrir el mismo hueco que
scripts/update_rfx20_spot.py llenó para el spot (2026-04-18 en adelante).

- Cartera Historica: un archivo por día hábil nuevo (mismo esquema que los
  ~1900 archivos existentes).
- Divisor: se consulta por día, pero solo se agrega una fila a divisores.csv
  cuando el valor cambia respecto a la fila anterior (mismo patrón disperso
  del archivo existente, no una fila por día).
- Cartera Vigente / Proyectada: son snapshots del estado "actual" (no series
  históricas por día) — se agrega un único archivo nuevo de cada una, con la
  fecha de vigencia que informa el propio endpoint.

Uso:
    uv run python -m scripts.backfill_rfx20_composition
"""

from __future__ import annotations

from datetime import date, datetime

import httpx
import polars as pl
from loguru import logger

from config.settings import settings
from ingestion.rfx20_composition_ws import fetch_divisor, fetch_historical, fetch_snapshot

_COMPOSITION_BASE = settings.RAW_DIR / "rfx20_composition"
_HISTORICA_DIR = _COMPOSITION_BASE / "Cartera Historica"
_VIGENTE_DIR = _COMPOSITION_BASE / "Cartera Vigente"
_PROYECTADA_DIR = _COMPOSITION_BASE / "Cartera Proyectada"
_DIVISORES_PATH = _COMPOSITION_BASE / "divisores.csv"


def _pending_dates() -> list[date]:
    """Fechas nuevas: las que scripts/update_rfx20_spot.py ya trajo del spot."""
    spot = pl.read_csv(
        _COMPOSITION_BASE / "historico_spot_rfx20.csv",
        separator=";", decimal_comma=True,
        schema_overrides={"fecha_precio": pl.Utf8, "valor": pl.Float64},
    ).with_columns(pl.col("fecha_precio").str.to_date("%Y-%m-%d"))

    existing_historica = {
        datetime.strptime(p.stem.removeprefix("cartera_historica_"), "%Y%m%d").date()
        for p in _HISTORICA_DIR.glob("cartera_historica_*.csv")
    }
    all_dates = spot["fecha_precio"].to_list()
    return sorted(d for d in all_dates if d not in existing_historica and d > date(2026, 4, 17))


def _write_historica(target_date: date, client: httpx.Client) -> bool:
    df = fetch_historical(target_date, client=client)
    if df.height == 0:
        return False
    path = _HISTORICA_DIR / f"cartera_historica_{target_date.strftime('%Y%m%d')}.csv"
    df.write_csv(path, separator=";")
    return True


def _decimal_comma(df: pl.DataFrame, col: str) -> pl.DataFrame:
    return df.with_columns(pl.col(col).cast(pl.Utf8).str.replace(".", ",", literal=True))


def _write_snapshot_files() -> None:
    snap = fetch_snapshot()

    current = snap.get("current", {})
    current_date = current.get("mdEntryDateTime", "")[:10]
    if current_date and current.get("instrument"):
        df = pl.DataFrame(current["instrument"]).select(
            pl.col("Symbol").alias("contrato"),
            pl.col("MDEntrySize").cast(pl.Float64).alias("cantidad"),
        )
        path = _VIGENTE_DIR / f"nvas_cantidades_{current_date.replace('-', '')}.csv"
        if not path.exists():
            _decimal_comma(df, "cantidad").write_csv(path, separator=";")
            logger.info(f"[backfill] Cartera Vigente: {path.name} ({df.height} tickers)")
        else:
            logger.info(f"[backfill] Cartera Vigente: {path.name} ya existe, no se pisa.")

    projected = snap.get("projected", {})
    projected_date = projected.get("mdEntryDateTime", "")[:10]
    if projected_date and projected.get("instrument"):
        df = pl.DataFrame(projected["instrument"]).select(
            pl.col("Symbol").alias("contrato"),
            pl.col("MDEntrySize").cast(pl.Float64).alias("cantidad"),
        )
        path = _PROYECTADA_DIR / f"proyectada_{projected_date.replace('-', '')}.csv"
        if not path.exists():
            _decimal_comma(df, "cantidad").write_csv(path, separator=";")
            logger.info(f"[backfill] Cartera Proyectada: {path.name} ({df.height} tickers)")
        else:
            logger.info(f"[backfill] Cartera Proyectada: {path.name} ya existe, no se pisa.")


def _update_divisores(divisor_by_date: dict[date, float]) -> None:
    existing = pl.read_csv(
        _DIVISORES_PATH, separator=";", decimal_comma=True,
        schema_overrides={"fecha_divisor": pl.Utf8, "divisor": pl.Float64},
    ).with_columns(pl.col("fecha_divisor").str.to_date("%d/%m/%Y"))

    last_value = existing.sort("fecha_divisor")["divisor"][-1]
    new_rows = []
    for d in sorted(divisor_by_date):
        value = divisor_by_date[d]
        if value != last_value:
            new_rows.append({"fecha_divisor": d, "divisor": value})
            last_value = value

    if not new_rows:
        logger.info("[backfill] Divisor: sin cambios respecto al último valor conocido.")
        return

    combined = pl.concat([
        existing.rename({}),
        pl.DataFrame(new_rows),
    ]).sort("fecha_divisor")

    out = combined.select(
        pl.col("fecha_divisor").dt.strftime("%d/%m/%Y"),
        pl.col("divisor"),
    )
    _decimal_comma(out, "divisor").write_csv(_DIVISORES_PATH, separator=";")
    logger.info(f"[backfill] Divisor: {len(new_rows)} fila(s) nueva(s) agregada(s) (cambios de valor).")


def main() -> None:
    dates = _pending_dates()
    if not dates:
        logger.info("[backfill] Nada pendiente — Cartera Historica ya cubre todas las fechas del spot.")
        return

    logger.info(f"[backfill] {len(dates)} fechas nuevas: {dates[0]} → {dates[-1]}")

    ok, failed = 0, []
    divisor_by_date: dict[date, float] = {}
    with httpx.Client(timeout=30, verify=False) as client:
        for d in dates:
            try:
                if _write_historica(d, client):
                    ok += 1
                else:
                    failed.append(d)
            except Exception as exc:
                logger.error(f"[backfill] Historica {d}: {exc}")
                failed.append(d)

            divisor = fetch_divisor(d, client=client)
            if divisor is not None:
                divisor_by_date[d] = divisor

    logger.info(f"[backfill] Cartera Historica: {ok} archivos escritos, {len(failed)} fallidos.")
    if failed:
        logger.warning(f"[backfill] Fechas sin datos históricos: {failed}")

    _update_divisores(divisor_by_date)
    _write_snapshot_files()

    logger.info(
        "[backfill] Listo. Correr `uv run python -m ingestion.composition_runner` "
        "para regenerar los parquets de raw/v1/ con todo esto."
    )


if __name__ == "__main__":
    main()
