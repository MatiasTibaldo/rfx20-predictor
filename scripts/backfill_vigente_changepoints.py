"""
Backfill de Cartera Vigente en los puntos de cambio real de composición
(no un archivo por día) — solo por esta vez, para completar el hueco entre
abril y agosto 2026 que scripts/backfill_rfx20_composition.py dejó (ese
script solo trajo un snapshot "actual" de /api/rfx20, no la secuencia de
cambios intermedios).

No pega a la API — deriva los puntos de cambio directamente de Cartera
Historica, que ya está completa día por día para este período (ver
docs/decisions/rfx20_ws_backfill.md). Se compara la composición
(ticker, cantidad) de cada rueda contra la anterior; cuando difiere, es un
punto de cambio real y se escribe un archivo de Cartera Vigente ahí, mismo
esquema que los archivos existentes (contrato;cantidad).

Cartera Proyectada no se backfillea de la misma forma: es una proyección
hacia adelante anunciada en un momento dado, no algo reconstruible desde
el historial de composición efectiva — no hay forma de recuperar qué se
proyectaba en fechas pasadas sin un endpoint que dé ese historial.

Uso:
    uv run python -m scripts.backfill_vigente_changepoints
"""

from __future__ import annotations

from datetime import date

import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

_VIGENTE_DIR = settings.RAW_DIR / "rfx20_composition" / "Cartera Vigente"
_GAP_START = date(2026, 4, 16)
_GAP_END = date(2026, 8, 25)


def _decimal_comma(df: pl.DataFrame, col: str) -> pl.DataFrame:
    return df.with_columns(pl.col(col).cast(pl.Utf8).str.replace(".", ",", literal=True))


def main() -> None:
    store = DuckDBStore()
    comp = store.load_parquet(layer="raw", name="rfx20_composition", version="v1").sort(
        ["date", "ticker"]
    )
    gap = comp.filter((pl.col("date") >= _GAP_START) & (pl.col("date") <= _GAP_END))
    dates = sorted(gap["date"].unique().to_list())

    change_dates: list[date] = []
    prev_snapshot = None
    for d in dates:
        day = gap.filter(pl.col("date") == d).select("ticker", "quantity").sort("ticker")
        snapshot = tuple(day.rows())
        if prev_snapshot is not None and snapshot != prev_snapshot:
            change_dates.append(d)
        prev_snapshot = snapshot

    logger.info(
        f"[backfill_vigente] {len(dates)} fechas revisadas, "
        f"{len(change_dates)} puntos de cambio real de composición: {change_dates}"
    )

    written = 0
    for d in change_dates:
        path = _VIGENTE_DIR / f"nvas_cantidades_{d.strftime('%Y%m%d')}.csv"
        if path.exists():
            logger.info(f"[backfill_vigente] {path.name} ya existe, no se pisa.")
            continue

        day_df = (
            gap.filter(pl.col("date") == d)
            .select(pl.col("ticker").alias("contrato"), pl.col("quantity").alias("cantidad"))
            .sort("contrato")
        )
        _decimal_comma(day_df, "cantidad").write_csv(path, separator=";")
        written += 1
        logger.info(f"[backfill_vigente] Escrito {path.name} ({day_df.height} tickers)")

    logger.info(
        f"[backfill_vigente] Listo — {written} archivo(s) nuevo(s) en Cartera Vigente/. "
        "No hace falta re-correr composition_runner: Vigente no alimenta "
        "rfx20_composition.parquet (eso viene solo de Historica, ya completa)."
    )


if __name__ == "__main__":
    main()
