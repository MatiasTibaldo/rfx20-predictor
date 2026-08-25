"""
Ingesta manual de futuros RFX20 (MatbaRofex).

Script de uso a demanda, no forma parte de los nodos del pipeline de
Streamlit — se corre cuando hace falta (re)descargar la serie de futuros
antes de correr Nodo 4. Persiste en data/raw/v1/rfx20_futures.parquet.

Uso:
    uv run python -m scripts.fetch_rfx20_futures
    uv run python -m scripts.fetch_rfx20_futures --from 2018-01-01 --to 2026-08-21
"""

from __future__ import annotations

import argparse
from datetime import date, datetime

from loguru import logger

from ingestion.futures import RfxFuturesConnector
from storage.store import DuckDBStore


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", type=_parse_date, default=date(2018, 1, 1))
    parser.add_argument("--to", dest="date_to", type=_parse_date, default=date.today())
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    connector = RfxFuturesConnector()
    df = connector.fetch("RFX20", args.date_from, args.date_to)

    store = DuckDBStore()
    path = store.save_parquet(df, layer="raw", name="rfx20_futures", version=args.version)

    logger.info(
        f"rfx20_futures: {len(df):,} filas, "
        f"{df['symbol'].n_unique()} contratos, "
        f"{df['date'].min()} → {df['date'].max()} → {path}"
    )


if __name__ == "__main__":
    main()
