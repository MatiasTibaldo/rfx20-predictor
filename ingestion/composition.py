"""
RFX20 index composition loader.

Reads historical, projected, and current cartera CSVs from the raw rfx20
directory, plus auxiliary spot-price and dividend files.  All outputs are
normalised Polars DataFrames with standardised column names.

Three CSV structures are supported:

* **Cartera Historica** — uniform schema across ~1 900 files; loaded via a
  single ``pl.scan_csv`` + glob for efficiency.
* **Cartera Proyectada** and **Cartera Vigente** — date comes from the
  filename, not the content; loaded via list-comprehension + ``pl.concat``.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import polars as pl
from loguru import logger

from storage.store import DuckDBStore

# Matches the 8-digit date embedded in all cartera filenames.
_DATE_RE: re.Pattern[str] = re.compile(r"(\d{8})")

_EMPTY_COMPOSITION = pl.DataFrame(
    schema={
        "date": pl.Date,
        "ticker": pl.Utf8,
        "quantity": pl.Float64,
        "source": pl.Utf8,
    }
)


def _yyyymmdd(s: str) -> date:
    """Parse an 8-digit YYYYMMDD string into a :class:`datetime.date`."""
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


class RFX20CompositionLoader:
    """Loads RFX20 index composition data from raw CSV flat files.

    All methods are stateless: they accept ``base_path`` (the directory
    that contains the three ``Cartera *`` sub-folders and the auxiliary
    CSV files) and return a normalised Polars DataFrame.

    Example::

        loader = RFX20CompositionLoader()
        base = Path("data/raw/rfx20_composition")
        df_hist = loader.load_historica(base)

        store = DuckDBStore()
        loader.save_to_raw(base, store)
    """

    # ------------------------------------------------------------------ #
    # Core loaders                                                          #
    # ------------------------------------------------------------------ #

    def load_historica(self, base_path: Path) -> pl.DataFrame:
        """Lazy-scan all Cartera Historica CSVs via glob (~1 900 files).

        Uses ``pl.scan_csv`` with a glob pattern so only one pass over the
        files is needed; schema is uniform across all files.

        Args:
            base_path: Root directory containing ``Cartera Historica/``.

        Returns:
            Columns: ``date`` (Date), ``ticker`` (Utf8), ``quantity`` (Float64),
            ``close`` (Float64), ``source`` (Utf8 = ``"historica"``).
            Sorted by ``date`` ascending.
        """
        pattern = str(base_path / "Cartera Historica" / "cartera_historica_*.csv")
        lf = pl.scan_csv(
            pattern,
            separator=";",
            schema_overrides={
                "ticker": pl.Utf8,
                "cantidades_vigentes": pl.Float64,
                "close": pl.Float64,
                "fecha_cantidades_vigentes": pl.Utf8,
                "fecha_precio": pl.Utf8,
            },
            try_parse_dates=False,
            null_values=["NA"],
        )
        df = (
            lf.select(
                pl.col("fecha_precio").str.to_date("%Y-%m-%d").alias("date"),
                pl.col("ticker"),
                pl.col("cantidades_vigentes").alias("quantity"),
                pl.col("close"),
                pl.lit("historica").cast(pl.Utf8).alias("source"),
            )
            .sort("date")
            .collect()
        )
        logger.info(
            f"[historica] {len(df):,} rows | "
            f"dates {df['date'].min()} → {df['date'].max()}"
        )
        return df

    def load_proyectada(self, base_path: Path) -> pl.DataFrame:
        """Read all Cartera Proyectada CSVs; date extracted from filename.

        Files use semicolon separator, comma decimal, and quoted fields.

        Args:
            base_path: Root directory containing ``Cartera Proyectada/``.

        Returns:
            Columns: ``date`` (Date), ``ticker`` (Utf8), ``quantity`` (Float64),
            ``source`` (Utf8 = ``"proyectada"``). Sorted by ``date`` ascending.
        """
        folder = base_path / "Cartera Proyectada"
        frames: list[pl.DataFrame] = []
        skipped = 0

        for fpath in sorted(folder.glob("proyectada_*.csv")):
            m = _DATE_RE.search(fpath.stem)
            if not m:
                logger.warning(f"[proyectada] Unmatched filename, skipping: {fpath.name}")
                skipped += 1
                continue
            file_date = _yyyymmdd(m.group(1))
            try:
                raw = pl.read_csv(
                    fpath,
                    separator=";",
                    decimal_comma=True,
                    schema_overrides={"contrato": pl.Utf8, "cantidad": pl.Float64},
                    quote_char='"',
                    null_values=["NA"],
                )
                frames.append(
                    raw.select(
                        pl.lit(file_date).alias("date"),
                        pl.col("contrato").alias("ticker"),
                        pl.col("cantidad").alias("quantity"),
                        pl.lit("proyectada").cast(pl.Utf8).alias("source"),
                    )
                )
            except Exception as exc:
                logger.warning(f"[proyectada] Failed to read {fpath.name}: {exc}")
                skipped += 1

        if skipped:
            logger.warning(f"[proyectada] Skipped {skipped} file(s)")
        if not frames:
            return _EMPTY_COMPOSITION.clone()

        df = pl.concat(frames).sort("date")
        logger.info(
            f"[proyectada] {len(df):,} rows from {len(frames)} files | "
            f"dates {df['date'].min()} → {df['date'].max()}"
        )
        return df

    def load_vigente(self, base_path: Path) -> pl.DataFrame:
        """Read all Cartera Vigente CSVs; date extracted from filename.

        Handles both quoted (``"contrato";"cantidad"``) and plain
        (``contrato;cantidad``) header/value variants transparently.
        Includes ``nvas_cantidades_pre_split_*.csv`` files.

        Args:
            base_path: Root directory containing ``Cartera Vigente/``.

        Returns:
            Columns: ``date`` (Date), ``ticker`` (Utf8), ``quantity`` (Float64),
            ``source`` (Utf8 = ``"vigente"``). Sorted by ``date`` ascending.
        """
        folder = base_path / "Cartera Vigente"
        frames: list[pl.DataFrame] = []
        skipped = 0

        for fpath in sorted(folder.glob("nvas_cantidades*.csv")):
            m = _DATE_RE.search(fpath.stem)
            if not m:
                logger.warning(f"[vigente] Unmatched filename, skipping: {fpath.name}")
                skipped += 1
                continue
            file_date = _yyyymmdd(m.group(1))
            try:
                raw = pl.read_csv(
                    fpath,
                    separator=";",
                    decimal_comma=True,
                    schema_overrides={"contrato": pl.Utf8, "cantidad": pl.Float64},
                    quote_char='"',
                    null_values=["NA"],
                )
                frames.append(
                    raw.select(
                        pl.lit(file_date).alias("date"),
                        pl.col("contrato").alias("ticker"),
                        pl.col("cantidad").alias("quantity"),
                        pl.lit("vigente").cast(pl.Utf8).alias("source"),
                    )
                )
            except Exception as exc:
                logger.warning(f"[vigente] Failed to read {fpath.name}: {exc}")
                skipped += 1

        if skipped:
            logger.warning(f"[vigente] Skipped {skipped} file(s)")
        if not frames:
            return _EMPTY_COMPOSITION.clone()

        df = pl.concat(frames).sort("date")
        logger.info(
            f"[vigente] {len(df):,} rows from {len(frames)} files | "
            f"dates {df['date'].min()} → {df['date'].max()}"
        )
        return df

    # ------------------------------------------------------------------ #
    # Query helpers                                                         #
    # ------------------------------------------------------------------ #

    def get_unique_tickers(
        self,
        base_path: Path,
        sources: list[str] | None = None,
    ) -> list[str]:
        """Return alphabetically sorted unique tickers from one or more sources.

        Args:
            base_path: Root rfx20 directory.
            sources: Cartera types to include.  Defaults to
                ``["historica"]``.

        Returns:
            Sorted list of unique ticker strings.
        """
        if sources is None:
            sources = ["historica"]

        _loaders = {
            "historica": self.load_historica,
            "proyectada": self.load_proyectada,
            "vigente": self.load_vigente,
        }

        frames: list[pl.DataFrame] = []
        files_per_source: dict[str, int] = {}

        for src in sources:
            if src not in _loaders:
                logger.warning(f"[get_unique_tickers] Unknown source '{src}', skipping")
                continue
            df = _loaders[src](base_path)
            # One unique date ≈ one source file for all three cartera types.
            files_per_source[src] = df["date"].n_unique()
            frames.append(df.select("ticker", "date"))

        if not frames:
            logger.warning("[get_unique_tickers] No data loaded — returning empty list")
            return []

        combined = pl.concat(frames)
        tickers = sorted(combined["ticker"].unique().to_list())
        date_min = combined["date"].min()
        date_max = combined["date"].max()

        logger.info(
            f"[get_unique_tickers] {len(tickers)} unique tickers | "
            f"dates {date_min} → {date_max} | "
            f"files by source: {files_per_source}"
        )
        return tickers

    def get_composition_at_date(
        self,
        base_path: Path,
        target_date: date,
        source: str = "historica",
    ) -> pl.DataFrame:
        """Return index composition for a given date.

        Falls back to the most recent available date strictly before
        ``target_date`` when an exact match does not exist.

        Args:
            base_path: Root rfx20 directory.
            target_date: Requested composition date.
            source: Cartera type — ``"historica"``, ``"proyectada"``, or
                ``"vigente"``.

        Returns:
            Filtered DataFrame for the resolved date.  Schema matches the
            corresponding ``load_*`` method.

        Raises:
            ValueError: If no data exists on or before ``target_date``.
        """
        _loaders = {
            "historica": self.load_historica,
            "proyectada": self.load_proyectada,
            "vigente": self.load_vigente,
        }
        if source not in _loaders:
            raise ValueError(f"Unknown source '{source}'. Choose from {list(_loaders)}")

        df = _loaders[source](base_path)

        # Collect all dates ≤ target_date, pick the most recent.
        candidate_dates = (
            df.filter(pl.col("date") <= pl.lit(target_date))["date"]
            .unique()
            .sort(descending=True)
        )
        if candidate_dates.is_empty():
            raise ValueError(
                f"No '{source}' data available on or before {target_date}"
            )

        resolved = candidate_dates[0]
        if resolved != target_date:
            logger.info(
                f"[get_composition_at_date] {target_date} not in '{source}'; "
                f"falling back to {resolved}"
            )
        return df.filter(pl.col("date") == resolved)

    # ------------------------------------------------------------------ #
    # Auxiliary series                                                      #
    # ------------------------------------------------------------------ #

    def load_spot_series(self, base_path: Path) -> pl.DataFrame:
        """Load the RFX20 historical spot-price series.

        Source file: ``historico_spot_rfx20.csv``
        Format: ``fecha_precio;valor`` — dates as YYYY-MM-DD, comma decimal.

        Args:
            base_path: Root rfx20 directory.

        Returns:
            Columns: ``date`` (Date), ``value`` (Float64). Sorted by ``date``.
        """
        fpath = base_path / "historico_spot_rfx20.csv"
        df = (
            pl.read_csv(
                fpath,
                separator=";",
                decimal_comma=True,
                schema_overrides={"fecha_precio": pl.Utf8, "valor": pl.Float64},
            )
            .select(
                pl.col("fecha_precio").str.to_date("%Y-%m-%d").alias("date"),
                pl.col("valor").alias("value"),
            )
            .sort("date")
        )
        logger.info(
            f"[spot] {len(df):,} rows | "
            f"dates {df['date'].min()} → {df['date'].max()}"
        )
        return df

    def load_dividends(self, base_path: Path) -> pl.DataFrame:
        """Load dividend adjustment events.

        Source file: ``base.dividendos2.csv``
        Format: ``Especie;Monto;Fecha de Ajuste;tipo`` — dates as DD/MM/YYYY,
        comma decimal.

        Args:
            base_path: Root rfx20 directory.

        Returns:
            Columns: ``ticker`` (Utf8), ``amount`` (Float64), ``date`` (Date),
            ``type`` (Utf8). Sorted by ``date``.
        """
        fpath = base_path / "base.dividendos2.csv"
        df = (
            pl.read_csv(
                fpath,
                separator=";",
                decimal_comma=True,
                schema_overrides={
                    "Especie": pl.Utf8,
                    "Monto": pl.Float64,
                    "Fecha de Ajuste": pl.Utf8,
                    "tipo": pl.Utf8,
                },
            )
            .select(
                pl.col("Especie").alias("ticker"),
                pl.col("Monto").alias("amount"),
                pl.col("Fecha de Ajuste").str.to_date("%d/%m/%Y").alias("date"),
                pl.col("tipo").alias("type"),
            )
            .sort("date")
        )
        logger.info(
            f"[dividends] {len(df):,} rows | "
            f"dates {df['date'].min()} → {df['date'].max()}"
        )
        return df

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def save_to_raw(self, base_path: Path, store: DuckDBStore) -> None:
        """Persist normalised DataFrames to Parquet via DuckDBStore.

        Saves three datasets under the ``raw`` layer, version ``v1``:

        * ``rfx20_composition`` — from :meth:`load_historica`
        * ``rfx20_spot`` — from :meth:`load_spot_series`
        * ``rfx20_dividends`` — from :meth:`load_dividends`

        Args:
            base_path: Root rfx20 directory.
            store: Initialised :class:`~storage.store.DuckDBStore` instance.
        """
        comp_df = self.load_historica(base_path)
        spot_df = self.load_spot_series(base_path)
        div_df = self.load_dividends(base_path)

        store.save_parquet(comp_df, layer="raw", name="rfx20_composition", version="v1")
        store.save_parquet(spot_df, layer="raw", name="rfx20_spot", version="v1")
        store.save_parquet(div_df, layer="raw", name="rfx20_dividends", version="v1")

        logger.info(
            "[save_to_raw] Done.\n"
            f"  rfx20_composition : {len(comp_df):,} rows | "
            f"{comp_df['date'].min()} → {comp_df['date'].max()} | "
            f"{comp_df['ticker'].n_unique()} tickers\n"
            f"  rfx20_spot        : {len(spot_df):,} rows | "
            f"{spot_df['date'].min()} → {spot_df['date'].max()}\n"
            f"  rfx20_dividends   : {len(div_df):,} rows | "
            f"{div_df['date'].min()} → {div_df['date'].max()} | "
            f"{div_df['ticker'].n_unique()} tickers"
        )
