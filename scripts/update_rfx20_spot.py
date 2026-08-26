"""
Actualización manual del spot histórico del RFX20 con el WS de MatbaRofex.

Trae el spot oficial desde la última fecha disponible en
historico_spot_rfx20.csv hasta hoy (o hasta --to) vía Rfx20IndexConnector,
y agrega SOLO fechas nuevas al CSV — nunca sobreescribe un valor histórico
ya presente. El archivo sigue siendo la fuente de verdad manual del spot,
esto es solo una forma de extenderlo sin depender de un export manual cada
vez.

No regenera automáticamente data/raw/v1/rfx20_spot.parquet — correr
`ingestion.composition_runner` después (o el botón "1. Composición RFX20"
en la app de Streamlit) para que el resto del pipeline vea los datos
nuevos.

Uso:
    uv run python -m scripts.update_rfx20_spot
    uv run python -m scripts.update_rfx20_spot --to 2026-08-25
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta

import polars as pl
from loguru import logger

from config.settings import settings
from ingestion.rfx20_index import Rfx20IndexConnector

_SPOT_PATH = settings.RAW_DIR / "rfx20_composition" / "historico_spot_rfx20.csv"


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--to", dest="date_to", type=_parse_date, default=date.today())
    args = parser.parse_args()

    existing = pl.read_csv(
        _SPOT_PATH, separator=";", decimal_comma=True,
        schema_overrides={"fecha_precio": pl.Utf8, "valor": pl.Float64},
    ).with_columns(pl.col("fecha_precio").str.to_date("%Y-%m-%d"))

    last_date = existing["fecha_precio"].max()
    date_from = last_date + timedelta(days=1)

    if date_from > args.date_to:
        logger.info(
            f"[update_rfx20_spot] Ya está al día: última fecha {last_date}, "
            f"nada que traer hasta {args.date_to}."
        )
        return

    logger.info(f"[update_rfx20_spot] Trayendo spot desde {date_from} hasta {args.date_to}.")
    connector = Rfx20IndexConnector()
    new_rows = connector.fetch("RFX20", date_from, args.date_to)

    if new_rows.height == 0:
        logger.warning("[update_rfx20_spot] La API no devolvió filas nuevas.")
        return

    combined = (
        pl.concat([
            existing.rename({"fecha_precio": "date", "valor": "value"}),
            new_rows,
        ])
        .unique(subset="date", keep="first")  # existing wins on any overlap
        .sort("date")
    )

    out = combined.select(
        pl.col("date").dt.strftime("%Y-%m-%d").alias("fecha_precio"),
        pl.col("value").alias("valor"),
    )
    # decimal_comma=True on read expects comma as decimal separator on write too
    out_str = out.with_columns(
        pl.col("valor").cast(pl.Utf8).str.replace(".", ",", literal=True)
    )
    out_str.write_csv(_SPOT_PATH, separator=";")

    logger.info(
        f"[update_rfx20_spot] {new_rows.height} filas nuevas agregadas "
        f"({new_rows['date'].min()} → {new_rows['date'].max()}). "
        f"Total ahora: {combined.height} filas ({combined['date'].min()} → {combined['date'].max()})."
    )
    logger.info(
        "[update_rfx20_spot] Correr `uv run python -m ingestion.composition_runner` "
        "para regenerar data/raw/v1/rfx20_spot.parquet."
    )


if __name__ == "__main__":
    main()
