"""
Conector para futuros del índice RFX20 (MatbaRofex).

Endpoint utilizado:
    GET https://apicem.matbarofex.com.ar/api/v2/closing-prices
    Params: product=RFX20, segment=Monedas, type=FUT, excludeEmptyVol=true,
            from, to, page, pageSize, sortDir, market=ROFX

Sin autenticación (API pública). Se pagina con page/pageSize/totalEntries
hasta reunir todas las filas del rango pedido.

Ver docs/decisions/futures_implied_rate.md: no hay mercado de opciones
líquido sobre RFX20, por lo que no se calcula una volatilidad implícita —
se usa el campo ``impliedRate`` (tasa de interés implícita, ya calculada
por MatbaRofex a partir del spot y el vencimiento) como feature de tasa
implícita, y la selección de contrato front-month se hace en
``features/macro.py`` a partir de los datos (sin calendario de vencimientos).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import polars as pl
from loguru import logger
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from ingestion.base import BaseConnector

_BASE_URL = "https://apicem.matbarofex.com.ar"
_ENDPOINT = "/api/v2/closing-prices"
_PAGE_SIZE = 200

# Mapeo de campos de la API → nombres canónicos snake_case.
_API_COLUMN_MAP: dict[str, str] = {
    "dateTime": "date",
    "symbol": "symbol",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "settlement": "settlement",
    "volume": "volume",
    "openInterest": "open_interest",
    "impliedRate": "implied_rate",
}

FUTURES_COLUMNS: list[str] = [
    "date", "symbol", "open", "high", "low", "close",
    "settlement", "volume", "open_interest", "implied_rate",
]


class RfxFuturesConnector(BaseConnector):
    """Obtiene precios de cierre diarios de futuros RFX20 desde MatbaRofex.

    A diferencia de :class:`ingestion.primary_rest.PrimaryRESTConnector`,
    no requiere sesión ni autenticación — cada request es independiente.

    Args:
        base_url: URL base de la API. Default: ``_BASE_URL``.
        timeout: Timeout por request en segundos.
        max_retries: Intentos ante errores de red o 5xx.
        page_size: Filas por página. Default 200.

    Example:
        >>> connector = RfxFuturesConnector()
        >>> df = connector.fetch("RFX20", date(2018, 1, 1), date(2026, 8, 21))
        >>> df.columns
        ['date', 'symbol', 'open', 'high', 'low', 'close', 'settlement',
         'volume', 'open_interest', 'implied_rate']
    """

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: int = 30,
        max_retries: int = 3,
        page_size: int = _PAGE_SIZE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._page_size = page_size

    @property
    def source_name(self) -> str:
        return "MatbaRofex closing-prices API"

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """Obtiene todos los precios de cierre de futuros de ``ticker`` en el rango.

        Pagina automáticamente hasta reunir ``totalEntries`` filas.

        Args:
            ticker: Producto MatbaRofex (ej: "RFX20").
            date_from: Fecha de inicio (inclusive).
            date_to: Fecha de fin (inclusive).

        Returns:
            DataFrame con columnas :data:`FUTURES_COLUMNS`, ordenado por
            ``date`` y ``symbol``.
        """
        self._log_fetch_start(ticker, date_from, date_to)

        records: list[dict[str, Any]] = []
        page = 1
        total_entries: int | None = None

        with httpx.Client(timeout=self._timeout) as client:
            while total_entries is None or len(records) < total_entries:
                params = {
                    "product": ticker,
                    "segment": "Monedas",
                    "type": "FUT",
                    "excludeEmptyVol": "true",
                    "from": date_from.isoformat(),
                    "to": date_to.isoformat(),
                    "page": page,
                    "pageSize": self._page_size,
                    "sortDir": "ASC",
                    "market": "ROFX",
                }
                raw = self._get_page(client, params)

                if not self.validate_response(raw):
                    raise ValueError(
                        f"Respuesta inválida de {self.source_name} para "
                        f"ticker={ticker!r}, page={page}. Datos: {str(raw)[:300]}"
                    )

                total_entries = raw["totalEntries"]
                records.extend(raw["data"])

                if not raw["data"]:
                    break
                page += 1

        df = self._parse_response(records)
        self._log_fetch_done(ticker, len(df))
        return df

    def validate_response(self, response: object) -> bool:
        """Verifica que la respuesta tiene ``data`` (lista) y ``totalEntries``."""
        if not isinstance(response, dict):
            return False
        return isinstance(response.get("data"), list) and "totalEntries" in response

    # ------------------------------------------------------------------ #
    # Internos                                                             #
    # ------------------------------------------------------------------ #

    def _get_page(self, client: httpx.Client, params: dict[str, Any]) -> dict:
        """GET de una página con reintentos ante errores de red / 5xx."""
        url = f"{self._base_url}{_ENDPOINT}"
        for attempt in Retrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((httpx.RequestError, ConnectionError)),
            reraise=True,
        ):
            with attempt:
                try:
                    response = client.get(url, params=params)
                except httpx.TimeoutException as exc:
                    raise httpx.RequestError(
                        f"Timeout ({self._timeout}s) al conectar con {url}"
                    ) from exc

                if response.is_server_error:
                    raise ConnectionError(
                        f"Error del servidor: HTTP {response.status_code} — "
                        f"{response.text[:200]}"
                    )

                response.raise_for_status()
                return response.json()

        raise ConnectionError(  # pragma: no cover
            f"No se pudo completar el request a {url} tras {self._max_retries} intentos."
        )

    def _parse_response(self, records: list[dict[str, Any]]) -> pl.DataFrame:
        """Convierte los registros JSON en un DataFrame con columnas canónicas."""
        if not records:
            return pl.DataFrame(
                {col: pl.Series([], dtype=pl.Float64) for col in FUTURES_COLUMNS}
            ).with_columns(
                pl.col("date").cast(pl.Date), pl.col("symbol").cast(pl.Utf8)
            )

        df = pl.DataFrame(records)
        rename_map = {c: _API_COLUMN_MAP[c] for c in df.columns if c in _API_COLUMN_MAP}
        df = df.rename(rename_map)

        df = df.with_columns(
            pl.col("date").str.slice(0, 10).str.to_date(format="%Y-%m-%d").alias("date")
        )
        for col in ("open", "high", "low", "close", "settlement", "volume",
                    "open_interest", "implied_rate"):
            if col in df.columns and df[col].dtype != pl.Float64:
                df = df.with_columns(pl.col(col).cast(pl.Float64))

        return df.select(FUTURES_COLUMNS).sort(["date", "symbol"])
