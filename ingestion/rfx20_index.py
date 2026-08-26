"""
Conector para el spot oficial del índice RFX20 (WS de MatbaRofex).

Endpoint utilizado:
    GET https://ws.matbarofex.com.ar:8999/api/rfx20/index?from={date}&to={date}

Devuelve el valor de cierre diario oficial del índice — mismo dato que
``data/raw/rfx20_composition/historico_spot_rfx20.csv``, pero permite traer
tramos recientes sin depender de un export manual. Sin autenticación, un
solo request cubre rangos de varios meses (no hace falta paginar).

Nota TLS: el certificado de ``ws.matbarofex.com.ar`` tiene la cadena
incompleta (falta el intermedio) — la verificación estándar falla incluso
con curl. Se deshabilita la verificación TLS explícitamente para este host
(``verify=False``), documentado acá en vez de silenciado. Es un endpoint
provisto directamente por el alumno (infraestructura de Primary S.A./
MatbaRofex), no una fuente de terceros no confiable.
"""

from __future__ import annotations

from datetime import date

import httpx
import polars as pl
from loguru import logger
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from ingestion.base import BaseConnector

_BASE_URL = "https://ws.matbarofex.com.ar:8999"
_ENDPOINT = "/api/rfx20/index"


class Rfx20IndexConnector(BaseConnector):
    """Obtiene el spot oficial diario del índice RFX20 desde el WS de MatbaRofex.

    Args:
        base_url: URL base del WS. Default: ``_BASE_URL``.
        timeout: Timeout por request en segundos.
        max_retries: Intentos ante errores de red o 5xx.

    Example:
        >>> connector = Rfx20IndexConnector()
        >>> df = connector.fetch("RFX20", date(2026, 4, 18), date(2026, 8, 25))
        >>> df.columns
        ['date', 'value']
    """

    def __init__(self, base_url: str = _BASE_URL, timeout: int = 30, max_retries: int = 3) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    @property
    def source_name(self) -> str:
        return "MatbaRofex RFX20 index WS"

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """Obtiene el spot oficial diario del RFX20 en el rango pedido.

        Args:
            ticker: Ignorado (el endpoint es específico del RFX20) — se
                mantiene por el contrato de BaseConnector.
            date_from: Fecha de inicio (inclusive).
            date_to: Fecha de fin (inclusive).

        Returns:
            DataFrame con columnas ``date`` (Date), ``value`` (Float64),
            ordenado por fecha.
        """
        self._log_fetch_start(ticker, date_from, date_to)

        url = f"{self._base_url}{_ENDPOINT}"
        params = {"from": date_from.isoformat(), "to": date_to.isoformat()}

        with httpx.Client(timeout=self._timeout, verify=False) as client:
            raw = self._get(client, url, params)

        if not self.validate_response(raw):
            raise ValueError(
                f"Respuesta inválida de {self.source_name}. Datos: {str(raw)[:300]}"
            )

        df = self._parse_response(raw)
        self._log_fetch_done(ticker, len(df))
        return df

    def validate_response(self, response: object) -> bool:
        return isinstance(response, list)

    def _get(self, client: httpx.Client, url: str, params: dict) -> list:
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
                        f"Error del servidor: HTTP {response.status_code} — {response.text[:200]}"
                    )
                response.raise_for_status()
                return response.json()

        raise ConnectionError(  # pragma: no cover
            f"No se pudo completar el request a {url} tras {self._max_retries} intentos."
        )

    def _parse_response(self, records: list) -> pl.DataFrame:
        if not records:
            return pl.DataFrame({"date": pl.Series([], dtype=pl.Date), "value": pl.Series([], dtype=pl.Float64)})

        df = pl.DataFrame(records)
        df = df.select(
            pl.col("date").str.to_date("%Y-%m-%d").alias("date"),
            pl.col("value").cast(pl.Float64),
        )
        return df.sort("date")
