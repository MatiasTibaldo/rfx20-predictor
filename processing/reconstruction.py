"""
RFX20 index reconstruction from constituent OHLCV series.

Reconstructs the index value as Σ(close_i × quantity_i) / divisor_t and
validates it against the official spot series loaded from the store.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from loguru import logger

from config.settings import settings
from storage.store import DuckDBStore

# See docs/decisions/base_change_oct2023.md for context.
BASE_CHANGE_CORRECTIONS: list[dict] = [
    {"date_from": "2023-09-29", "date_to": "2023-10-06", "factor": 10.0},
]


def load_divisores(path: Path) -> pl.DataFrame:
    """Load the RFX20 divisor series from the CSV file.

    Expects a semicolon-separated file with comma as the decimal separator
    and dates formatted as ``%d/%m/%Y``.

    Args:
        path: Path to ``divisores.csv``.

    Returns:
        DataFrame with columns ``date`` (Date) and ``divisor`` (Float64),
        sorted ascending by date.
    """
    raw = pl.read_csv(path, separator=";", decimal_comma=True)

    # Normalize column names to lowercase and strip whitespace.
    raw = raw.rename({c: c.strip().lower() for c in raw.columns})

    date_col = next(c for c in raw.columns if "fecha" in c or c == "date")
    div_col = next(c for c in raw.columns if "divis" in c and "fecha" not in c)

    result = (
        raw.select(
            pl.col(date_col)
            .str.strptime(pl.Date, format="%d/%m/%Y")
            .alias("date"),
            pl.col(div_col).cast(pl.Float64).alias("divisor"),
        )
        .sort("date")
    )
    logger.info(f"[reconstruction] Loaded {len(result):,} divisor rows from {path}.")
    return result


def reconstruct_index(
    ohlcv_by_ticker: dict[str, pl.DataFrame],
    composition: pl.DataFrame,
    divisores: pl.DataFrame,
) -> pl.DataFrame:
    """Reconstruct the RFX20 index value from constituent series.

    Formula: index_t = Σ_i(close_i_t × quantity_i_t) / divisor_t

    The divisor is forward-filled to cover trading days between official
    publication dates.

    Args:
        ohlcv_by_ticker: Mapping of ticker → OHLCV DataFrame (requires
            ``date`` and ``close`` columns).
        composition: Index composition DataFrame with columns
            ``date`` (Date), ``ticker`` (String), ``quantity`` (Float64).
        divisores: Divisor series with ``date`` (Date) and ``divisor`` (Float64).

    Returns:
        DataFrame with columns ``date`` (Date) and ``reconstructed`` (Float64).
    """
    if not ohlcv_by_ticker:
        return pl.DataFrame(schema={"date": pl.Date, "reconstructed": pl.Float64})

    closes = pl.concat(
        [
            df.select("date", "close").with_columns(
                pl.lit(ticker.upper()).alias("ticker")
            )
            for ticker, df in ohlcv_by_ticker.items()
        ],
        how="diagonal",
    )

    numerator = (
        composition.select("date", "ticker", "quantity")
        .join(closes, on=["date", "ticker"], how="inner")
        .with_columns((pl.col("close") * pl.col("quantity")).alias("weighted_close"))
        .group_by("date")
        .agg(pl.col("weighted_close").sum().alias("numerator"))
        .sort("date")
    )

    # Forward-fill the divisor to every date present in the numerator.
    div_filled = (
        numerator.select("date")
        .join(divisores, on="date", how="left")
        .sort("date")
        .with_columns(pl.col("divisor").forward_fill())
    )

    result = (
        numerator.join(div_filled, on="date", how="left")
        .with_columns(
            (pl.col("numerator") / pl.col("divisor")).alias("reconstructed")
        )
        .select("date", "reconstructed")
        .sort("date")
    )

    for correction in BASE_CHANGE_CORRECTIONS:
        date_from = pl.date(int(correction["date_from"][:4]),
                            int(correction["date_from"][5:7]),
                            int(correction["date_from"][8:10]))
        date_to   = pl.date(int(correction["date_to"][:4]),
                            int(correction["date_to"][5:7]),
                            int(correction["date_to"][8:10]))
        result = result.with_columns(
            pl.when(
                (pl.col("date") >= date_from) & (pl.col("date") <= date_to)
            )
            .then(pl.col("reconstructed") * correction["factor"])
            .otherwise(pl.col("reconstructed"))
            .alias("reconstructed")
        )

    logger.info(
        f"[reconstruction] Reconstructed index: {len(result):,} days, "
        f"range {result['date'].min()} → {result['date'].max()}."
    )
    return result


def validate_reconstruction(
    reconstructed: pl.DataFrame,
    store: DuckDBStore,
    version: str = "v1",
    tolerance_pct: float = 1.0,
) -> pl.DataFrame:
    """Compare the reconstructed index against the official spot series.

    Args:
        reconstructed: DataFrame with ``date`` and ``reconstructed`` columns.
        store: DuckDBStore used to load the spot series.
        version: Version tag for the spot Parquet file.
        tolerance_pct: Days where ``|pct_error| > tolerance_pct`` are flagged.

    Returns:
        DataFrame with columns ``date`` (Date), ``reconstructed`` (Float64),
        ``spot`` (Float64), ``pct_error`` (Float64), ``flag`` (Boolean).
    """
    spot = store.load_parquet(layer="raw", name="rfx20_spot", version=version)

    result = (
        reconstructed.join(spot.rename({"value": "spot"}), on="date", how="inner")
        .with_columns(
            (
                (pl.col("reconstructed") - pl.col("spot")).abs()
                / pl.col("spot")
                * 100
            ).alias("pct_error")
        )
        .with_columns((pl.col("pct_error") > tolerance_pct).alias("flag"))
        .select("date", "reconstructed", "spot", "pct_error", "flag")
    )

    flagged = result.filter(pl.col("flag")).height
    logger.info(
        f"[reconstruction] Validation: {flagged}/{result.height} days flagged "
        f"(tolerance={tolerance_pct}%)."
    )
    return result


def run(
    ohlcv_by_ticker: dict[str, pl.DataFrame],
    composition: pl.DataFrame,
    store: DuckDBStore,
    version: str = "v1",
    divisores_path: Path | None = None,
    tolerance_pct: float = 1.0,
) -> pl.DataFrame:
    """Orchestrate divisor loading, index reconstruction, and spot validation.

    Args:
        ohlcv_by_ticker: Mapping of ticker → processed OHLCV DataFrame.
        composition: Index composition DataFrame.
        store: DuckDBStore for loading the spot series.
        version: Version tag.
        divisores_path: Path to ``divisores.csv``. Defaults to
            ``data/raw/rfx20_composition/divisores.csv``.
        tolerance_pct: Flagging threshold forwarded to
            :func:`validate_reconstruction`.

    Returns:
        Validation DataFrame from :func:`validate_reconstruction`.
    """
    path = divisores_path or (
        settings.RAW_DIR / "rfx20_composition" / "divisores.csv"
    )
    divisores = load_divisores(path)
    reconstructed = reconstruct_index(ohlcv_by_ticker, composition, divisores)
    return validate_reconstruction(reconstructed, store, version, tolerance_pct)
