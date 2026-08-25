"""
Macro features: spreads cambiarios, tasas, riesgo país, IPC con lag de
publicación, y tasa implícita/term spread de futuros RFX20.

Todas las fuentes tienen frecuencia y calendario distintos entre sí (IPC es
mensual, BADLAR/TAMAR y futuros tienen gaps, los dólares son diarios). Se
consolidan sobre una grilla diaria fija (la del propio índice RFX20, ver
:func:`build_macro_features`) usando ``join_asof(strategy="backward")`` —
cada fecha de la grilla toma el último valor conocido a esa fecha, nunca
uno futuro. Ver docs/decisions/macro_features_etapa2.md para el detalle de
cada decisión de diseño (por qué "venta", por qué el front-month de
futuros se resuelve sin calendario de vencimientos).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

# ------------------------------------------------------------------ #
# Spreads cambiarios                                                   #
# ------------------------------------------------------------------ #


def load_dolar_spreads(macro_dir: Path | None = None) -> pl.DataFrame:
    """Compute exchange-rate spreads from the daily dolar_*.csv series.

    Uses the ``venta`` price consistently across all five series (MEP and
    CCL already carry ``compra == venta``).

    Args:
        macro_dir: Directory with the dolar_*.csv files. Defaults to
            ``settings.RAW_DIR / "macro"``.

    Returns:
        DataFrame with ``date`` and four spread columns (fractional, not
        percentage): ``spread_oficial_informal``, ``spread_oficial_mep``,
        ``spread_oficial_ccl``, ``spread_mep_ccl``.
    """
    macro_dir = macro_dir or settings.RAW_DIR / "macro"

    def _load_venta(name: str) -> pl.DataFrame:
        df = pl.read_csv(macro_dir / f"{name}.csv")
        df = df.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))
        return df.select("date", pl.col("venta").alias(name))

    oficial = _load_venta("dolar_oficial")
    informal = _load_venta("dolar_informal")
    mep = _load_venta("dolar_mep")
    ccl = _load_venta("dolar_ccl")

    df = (
        oficial.join(informal, on="date", how="full", coalesce=True)
        .join(mep, on="date", how="full", coalesce=True)
        .join(ccl, on="date", how="full", coalesce=True)
        .sort("date")
    )

    # The full-join union of dates means a date where only one series
    # published still gets a row, with null in the others' columns —
    # forward-fill each raw column now (before deriving spreads) so those
    # union-only dates carry the last known value instead of a spurious
    # null that would later shadow the true value in the asof join onto
    # the trading calendar. Leading nulls (before a series existed, e.g.
    # MEP pre-2018-10-29) are correctly left as null.
    df = df.with_columns(
        pl.col("dolar_oficial").fill_null(strategy="forward"),
        pl.col("dolar_informal").fill_null(strategy="forward"),
        pl.col("dolar_mep").fill_null(strategy="forward"),
        pl.col("dolar_ccl").fill_null(strategy="forward"),
    )

    df = df.with_columns(
        ((pl.col("dolar_informal") - pl.col("dolar_oficial")) / pl.col("dolar_oficial")).alias(
            "spread_oficial_informal"
        ),
        ((pl.col("dolar_mep") - pl.col("dolar_oficial")) / pl.col("dolar_oficial")).alias(
            "spread_oficial_mep"
        ),
        ((pl.col("dolar_ccl") - pl.col("dolar_oficial")) / pl.col("dolar_oficial")).alias(
            "spread_oficial_ccl"
        ),
        ((pl.col("dolar_ccl") - pl.col("dolar_mep")) / pl.col("dolar_mep")).alias(
            "spread_mep_ccl"
        ),
    )

    result = df.select(
        "date",
        "spread_oficial_informal",
        "spread_oficial_mep",
        "spread_oficial_ccl",
        "spread_mep_ccl",
    )
    logger.debug(f"[macro] load_dolar_spreads: {result.height:,} rows.")
    return result


# ------------------------------------------------------------------ #
# Tasas y riesgo país                                                  #
# ------------------------------------------------------------------ #


def load_rates_and_risk(macro_dir: Path | None = None) -> pl.DataFrame:
    """Load riesgo país, tasa de plazo fijo, BADLAR and TAMAR, joined by date.

    Args:
        macro_dir: Directory with the source CSVs. Defaults to
            ``settings.RAW_DIR / "macro"``.

    Returns:
        DataFrame with ``date``, ``riesgo_pais``, ``tasa_pf``, ``badlar``,
        ``tamar``. ``tamar`` is null before 2024-10-01 (series starts there).
    """
    macro_dir = macro_dir or settings.RAW_DIR / "macro"

    riesgo = pl.read_csv(macro_dir / "riesgo_pais.csv").with_columns(
        pl.col("date").str.to_date("%Y-%m-%d")
    )
    tasa_pf = pl.read_csv(macro_dir / "tasa_plazo_fijo.csv").with_columns(
        pl.col("date").str.to_date("%Y-%m-%d")
    )

    badlar = pl.read_csv(macro_dir / "badlar.csv")
    badlar = badlar.rename({badlar.columns[0]: "date", badlar.columns[1]: "badlar"})
    badlar = badlar.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    tamar = pl.read_csv(macro_dir / "tamar.csv")
    tamar = tamar.rename({tamar.columns[0]: "date", tamar.columns[1]: "tamar"})
    tamar = tamar.with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    result = (
        riesgo.join(tasa_pf, on="date", how="full", coalesce=True)
        .join(badlar, on="date", how="full", coalesce=True)
        .join(tamar, on="date", how="full", coalesce=True)
        .sort("date")
    )

    # Same union-of-dates issue as load_dolar_spreads: forward-fill each
    # column so a date where only one source published doesn't shadow the
    # others' last known value in the asof join onto the trading calendar.
    result = result.with_columns(
        pl.col("riesgo_pais").fill_null(strategy="forward"),
        pl.col("tasa_pf").fill_null(strategy="forward"),
        pl.col("badlar").fill_null(strategy="forward"),
        pl.col("tamar").fill_null(strategy="forward"),
    )
    logger.debug(f"[macro] load_rates_and_risk: {result.height:,} rows.")
    return result


# ------------------------------------------------------------------ #
# IPC con lag de publicación (ver docs/decisions/ipc_publication_lag.md) #
# ------------------------------------------------------------------ #

# Mes de referencia (YYYY-MM) → fecha real de publicación (INDEC).
# Relevado a mano de los calendarios de difusión semestrales de INDEC.
_IPC_LAG_TABLE: dict[str, str] = {
    "2023-12": "2024-01-11", "2024-01": "2024-02-14", "2024-02": "2024-03-12",
    "2024-03": "2024-04-12", "2024-04": "2024-05-14", "2024-05": "2024-06-13",
    "2024-06": "2024-07-12", "2024-07": "2024-08-14", "2024-08": "2024-09-11",
    "2024-09": "2024-10-10", "2024-10": "2024-11-12", "2024-11": "2024-12-11",
    "2024-12": "2025-01-14", "2025-01": "2025-02-13", "2025-02": "2025-03-14",
    "2025-03": "2025-04-11", "2025-04": "2025-05-14", "2025-05": "2025-06-12",
    "2025-06": "2025-07-14", "2025-07": "2025-08-13", "2025-08": "2025-09-10",
    "2025-09": "2025-10-14", "2025-10": "2025-11-12", "2025-11": "2025-12-11",
    "2025-12": "2026-01-13", "2026-01": "2026-02-10", "2026-02": "2026-03-12",
    "2026-03": "2026-04-14", "2026-04": "2026-05-14", "2026-05": "2026-06-11",
}

_IPC_LAG_APPROXIMATION_DAYS = 12


def _approximate_availability(month_end: date) -> date:
    """Approximate publication date for months outside :data:`_IPC_LAG_TABLE`.

    month_end + 12 días corridos, rolled forward to the next weekday if it
    falls on a weekend (see docs/decisions/ipc_publication_lag.md).
    """
    availability = month_end + timedelta(days=_IPC_LAG_APPROXIMATION_DAYS)
    while availability.weekday() >= 5:  # Saturday=5, Sunday=6
        availability += timedelta(days=1)
    return availability


def load_ipc_with_lag(path: Path | None = None) -> pl.DataFrame:
    """Load IPC.csv and shift each observation to its real availability date.

    Args:
        path: Path to IPC.csv. Defaults to ``settings.RAW_DIR / "macro" / "IPC.csv"``.

    Returns:
        DataFrame with ``date`` (real publication/availability date, not
        month-end close date) and ``ipc_pct``.
    """
    path = path or settings.RAW_DIR / "macro" / "IPC.csv"
    raw = pl.read_csv(path).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    records = []
    for row in raw.iter_rows(named=True):
        month_end: date = row["date"]
        month_key = f"{month_end.year:04d}-{month_end.month:02d}"
        if month_key in _IPC_LAG_TABLE:
            availability = datetime.strptime(_IPC_LAG_TABLE[month_key], "%Y-%m-%d").date()
        else:
            availability = _approximate_availability(month_end)
        records.append({"date": availability, "ipc_pct": row["ipc_pct"]})

    result = pl.DataFrame(records).sort("date")
    logger.debug(f"[macro] load_ipc_with_lag: {result.height:,} rows.")
    return result


# ------------------------------------------------------------------ #
# Futuros RFX20 — front-month, tasa implícita, term spread              #
# ------------------------------------------------------------------ #


def select_front_month(futures_df: pl.DataFrame) -> pl.DataFrame:
    """Pick the front-month and next-month contract per date, from the data itself.

    No expiry calendar is kept — for each date, among the symbols that
    actually traded that day, the one with the smallest (year, month)
    parsed from ``RFX20{MM}{YYYY}`` is the front-month; the next by order
    is "next month". See docs/decisions/macro_features_etapa2.md.

    Args:
        futures_df: Raw futures DataFrame (``ingestion.futures.RfxFuturesConnector``
            output), with ``date``, ``symbol``, ``implied_rate`` columns.

    Returns:
        DataFrame with ``date``, ``implied_rate_front``, ``implied_rate_next``
        (null on dates with only one live contract), ``term_spread_futures``
        (``implied_rate_front - implied_rate_next``), ``futures_front_symbol``.
    """
    parsed = futures_df.with_columns(
        pl.col("symbol").str.slice(5, 2).cast(pl.Int32).alias("_month"),
        pl.col("symbol").str.slice(7, 4).cast(pl.Int32).alias("_year"),
    )
    parsed = parsed.with_columns(
        (pl.col("_year") * 100 + pl.col("_month")).alias("_rank_key")
    )
    parsed = parsed.sort(["date", "_rank_key"]).with_columns(
        pl.col("_rank_key").rank("ordinal").over("date").alias("_rank")
    )

    front = parsed.filter(pl.col("_rank") == 1).select(
        "date",
        pl.col("symbol").alias("futures_front_symbol"),
        pl.col("implied_rate").alias("implied_rate_front"),
    )
    next_month = parsed.filter(pl.col("_rank") == 2).select(
        "date", pl.col("implied_rate").alias("implied_rate_next")
    )

    result = front.join(next_month, on="date", how="left").with_columns(
        (pl.col("implied_rate_front") - pl.col("implied_rate_next")).alias(
            "term_spread_futures"
        )
    )
    result = result.select(
        "date", "implied_rate_front", "implied_rate_next", "term_spread_futures",
        "futures_front_symbol",
    ).sort("date")
    logger.debug(f"[macro] select_front_month: {result.height:,} rows.")
    return result


# ------------------------------------------------------------------ #
# Consolidación en la grilla diaria                                    #
# ------------------------------------------------------------------ #


def build_macro_features(
    trading_dates: pl.Series,
    store: DuckDBStore | None = None,
    version: str = "v1",
) -> pl.DataFrame:
    """Join all macro sources onto a fixed daily trading calendar.

    Each source keeps its own native frequency/calendar (IPC monthly,
    BADLAR/TAMAR/dolar daily-with-gaps, futures daily-with-gaps) and is
    aligned to ``trading_dates`` with ``join_asof(strategy="backward")`` —
    every date gets the last known value as of that date, never a future
    one. Requires ``data/raw/{version}/rfx20_futures.parquet`` to already
    exist (see ``scripts/fetch_rfx20_futures.py``).

    Args:
        trading_dates: Calendar to align to (see
            docs/decisions/macro_features_etapa2.md — uses the RFX20 index's
            own trading dates).
        store: DuckDBStore for loading the raw futures parquet.
        version: Data version tag.

    Returns:
        DataFrame with one row per date in ``trading_dates`` and all macro
        feature columns.
    """
    store = store or DuckDBStore()

    calendar = pl.DataFrame({"date": trading_dates}).unique().sort("date")

    futures_raw = store.load_parquet(layer="raw", name="rfx20_futures", version=version)

    sources = [
        load_dolar_spreads(),
        load_rates_and_risk(),
        load_ipc_with_lag(),
        select_front_month(futures_raw),
    ]

    result = calendar
    for source in sources:
        result = result.join_asof(source.sort("date"), on="date", strategy="backward")

    logger.info(
        f"[macro] build_macro_features done: {result.height:,} rows, "
        f"{len(result.columns)} columns."
    )
    return result
