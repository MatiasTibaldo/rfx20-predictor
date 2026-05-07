"""
Conector OHLCV diario histórico para la API REST de Primary S.A. (Matriz xoms).

Endpoint utilizado:
    GET /api/v2/series/securities/{instrument_id}
    Params: resolution=D, from={ISO datetime con TZ Argentina}, to={ISO datetime con TZ Argentina}

Autenticación:
    Cookie de sesión gestionada por AuthManager (flujo CSRF). El cliente httpx
    se obtiene via auth_manager.get_client() y reenvía las cookies automáticamente.

Retry policy:
    - Ante 401/403 (sesión expirada): llama auth_manager.reauth() y reintenta UNA vez.
      Este reintento es independiente del mecanismo de tenacity.
    - Ante 5xx o timeout de red: tenacity aplica backoff exponencial hasta
      PRIMARY_MAX_RETRIES intentos.

Design decision — httpx síncrono:
    Se usa httpx.Client (sync) obtenido del AuthManager porque el pipeline es
    actualmente síncrono y la sesión (cookie jar) debe persistir entre requests.
    La migración a async requeriría cambiar a AsyncClient en AuthManager.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx
import pytz
import polars as pl
from loguru import logger
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import settings
from ingestion.auth import AuthError, AuthManager
from ingestion.base import BaseConnector
from ingestion.instruments import RESOLUTION_DAILY, ticker_to_instrument_id

# Zona horaria de Argentina (sin DST).
_TZ_ARGENTINA = pytz.timezone("America/Argentina/Buenos_Aires")

# Endpoint relativo de series históricas.
_SERIES_ENDPOINT = "/api/v2/series/securities/{instrument_id}"

# Mapeo de campos de la API → nombres canónicos del pipeline.
# Estructura real confirmada de la respuesta:
#   {"nextTime": "...", "noData": false, "series": [
#       {"c": 944.0, "d": "2024-11-28T00:00:00Z", "h": 950.0,
#        "l": 937.0, "o": 940.0, "r": "D", "sid": "bm_MERV_ALUA_24hs", "v": 658186.0},
#       ...
#   ]}
# Campos "r" (resolution) y "sid" (instrument_id) se descartan en el parsing.
_API_COLUMN_MAP: dict[str, str] = {
    "o": "open",
    "h": "high",
    "l": "low",
    "c": "close",
    "v": "volume",
    "d": "date",   # ISO datetime UTC, ej: "2024-11-28T00:00:00Z" → date(2024, 11, 28)
}

# Columnas canónicas del DataFrame de salida (orden fijo).
OHLCV_COLUMNS: list[str] = ["date", "open", "high", "low", "close", "volume", "ticker"]


class PrimaryRESTConnector(BaseConnector):
    """Obtiene series OHLCV diarias históricas desde la API REST de Primary S.A.

    Convierte tickers MERVAL (ej: "ALUA") a instrument_ids de la API
    (ej: "bm_MERV_ALUA_24hs") via el módulo ``instruments``.

    Args:
        auth_manager: Instancia de AuthManager. Si se omite, se crea una desde settings.
        base_url: URL base de la API. Si se omite, se lee de settings.
        timeout: Timeout por request en segundos. Default: settings.PRIMARY_TIMEOUT.
        max_retries: Intentos ante errores de red o 5xx. Default: settings.PRIMARY_MAX_RETRIES.

    Example:
        >>> connector = PrimaryRESTConnector()
        >>> df = connector.fetch("ALUA", date(2024, 1, 1), date(2024, 12, 31))
        >>> df.columns
        ['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']
    """

    def __init__(
        self,
        auth_manager: AuthManager | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._auth = auth_manager or AuthManager()
        self._base_url = (base_url or settings.PRIMARY_BASE_URL).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.PRIMARY_TIMEOUT
        self._max_retries = (
            max_retries if max_retries is not None else settings.PRIMARY_MAX_RETRIES
        )

    @property
    def source_name(self) -> str:
        return "Primary REST API"

    # ------------------------------------------------------------------ #
    # Interfaz pública                                                     #
    # ------------------------------------------------------------------ #

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """Obtiene OHLCV diario para un instrumento en el rango dado.

        Pasos internos:
        1. Convierte ticker → instrument_id (ej: ALUA → bm_MERV_ALUA_24hs).
        2. Formatea fechas con TZ America/Argentina/Buenos_Aires.
        3. GET /api/v2/series/securities/{instrument_id} con params resolution, from, to.
        4. Ante 401/403: reauth() + un reintento.
        5. Ante 5xx/timeout: tenacity con backoff exponencial.
        6. Parsea y normaliza la respuesta a columnas estándar.

        Args:
            ticker: Símbolo del instrumento (ej: "ALUA", "GGAL").
            date_from: Fecha de inicio (inclusive).
            date_to: Fecha de fin (inclusive).

        Returns:
            DataFrame con columnas: date, open, high, low, close, volume, ticker.

        Raises:
            AuthError: Si la autenticación falla de forma irrecuperable.
            ConnectionError: Si se agotan los reintentos de red.
            ValueError: Si la respuesta de la API no tiene el formato esperado.
        """
        self._log_fetch_start(ticker, date_from, date_to)

        instrument_id = ticker_to_instrument_id(ticker)
        url = f"{self._base_url}{_SERIES_ENDPOINT.format(instrument_id=instrument_id)}"
        params = {
            "resolution": RESOLUTION_DAILY,
            "from": _format_date_tz(date_from),
            "to": _format_date_tz(date_to),
        }

        logger.debug(f"[{self.source_name}] GET {url} | params={params}")

        try:
            raw_data = self._fetch_with_auth_retry(url, params)
        except httpx.HTTPStatusError as exc:
            # Errores 4xx (salvo 401/403 que ya maneja _fetch_with_auth_retry)
            # indican rango inválido o instrumento sin datos — no es un fallo del pipeline.
            if exc.response.is_client_error:
                logger.warning(
                    f"[{self.source_name}] HTTP {exc.response.status_code} para "
                    f"ticker={ticker!r} from={date_from} to={date_to} — "
                    "rango inválido o sin datos; retornando DataFrame vacío."
                )
                return _empty_ohlcv_df(ticker)
            raise

        # noData indica que no hay datos ANTERIORES a la fecha solicitada (no que
        # la respuesta esté vacía). Es puramente informativo; se procesan las filas
        # que vengan en "series" independientemente de su valor.
        if isinstance(raw_data, dict):
            logger.debug(
                f"[{self.source_name}] noData={raw_data.get('noData')} "
                f"| ticker={ticker!r}"
            )

        if not self.validate_response(raw_data):
            raise ValueError(
                f"Respuesta inválida de {self.source_name} para ticker={ticker!r}. "
                f"Datos recibidos: {str(raw_data)[:300]}"
            )

        df = self._parse_response(raw_data, ticker)
        date_min = df["date"].min() if len(df) > 0 else None
        logger.info(
            f"[{self.source_name}] fetch done | ticker={ticker!r} "
            f"rows={len(df):,} date_min={date_min}"
        )
        return df

    def validate_response(self, response: object) -> bool:
        """Verifica que la respuesta JSON tiene la estructura esperada de la API.

        Formato válido:
            {"nextTime": "...", "noData": false, "series": [...]}

        Rechaza si:
        - No es un dict
        - No tiene clave "series"

        Nota: ``noData=True`` se maneja en ``fetch()`` antes de llegar aquí.

        Args:
            response: Body JSON parseado.

        Returns:
            True si la respuesta contiene una lista "series" procesable,
            incluyendo listas vacías (0 registros es un resultado válido).
        """
        if not isinstance(response, dict):
            return False
        if "series" not in response:
            return False
        return isinstance(response["series"], list)

    # ------------------------------------------------------------------ #
    # Lógica de autenticación y retry                                      #
    # ------------------------------------------------------------------ #

    def _fetch_with_auth_retry(self, url: str, params: dict[str, str]) -> Any:
        """Ejecuta el GET con manejo de sesión expirada (401/403).

        Ante 401/403: llama reauth() una vez y reintenta. Esta lógica es
        independiente del retry de tenacity (que cubre 5xx y errores de red).

        Args:
            url: URL completa del endpoint.
            params: Query params del request.

        Returns:
            Body JSON parseado.

        Raises:
            AuthError: Si la sesión no se puede renovar.
            ConnectionError: Si se agotan los reintentos de red/5xx.
        """
        response = self._get_raw(url, params)

        if response.status_code in (401, 403):
            logger.warning(
                f"[{self.source_name}] HTTP {response.status_code} — "
                "sesión expirada, re-autenticando."
            )
            self._auth.reauth()
            response = self._get_raw(url, params)

            if response.status_code in (401, 403):
                raise AuthError(
                    f"Auth fallida después de reauth: HTTP {response.status_code}. "
                    "Verificar credenciales."
                )

        response.raise_for_status()
        return response.json()

    def _get_raw(self, url: str, params: dict[str, str]) -> httpx.Response:
        """HTTP GET con reintentos por backoff exponencial ante 5xx y timeouts.

        Usa tenacity para reintentar hasta self._max_retries veces ante:
        - httpx.RequestError (conexión rechazada, timeout de red, etc.)
        - ConnectionError (error 5xx del servidor)

        Args:
            url: URL completa.
            params: Query params.

        Returns:
            httpx.Response (puede ser 401/403 — el caller los maneja).

        Raises:
            ConnectionError: Si se agotan los reintentos.
        """
        for attempt in Retrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((httpx.RequestError, ConnectionError)),
            reraise=True,
        ):
            with attempt:
                client = self._auth.get_client()
                try:
                    response = client.get(url, params=params, timeout=self._timeout)
                except httpx.TimeoutException as exc:
                    # Normalizar timeout a RequestError para que tenacity lo capture
                    raise httpx.RequestError(
                        f"Timeout ({self._timeout}s) al conectar con {url}"
                    ) from exc

                if response.is_server_error:
                    raise ConnectionError(
                        f"Error del servidor: HTTP {response.status_code} — "
                        f"{response.text[:200]}"
                    )

                return response

        # Unreachable (tenacity con reraise=True relanza antes de llegar acá),
        # pero satisface el type checker.
        raise ConnectionError(  # pragma: no cover
            f"No se pudo completar el request a {url} tras {self._max_retries} intentos."
        )

    # ------------------------------------------------------------------ #
    # Parsing y normalización de respuesta                                 #
    # ------------------------------------------------------------------ #

    def _parse_response(self, raw: dict[str, Any], ticker: str) -> pl.DataFrame:
        """Convierte el JSON de la API en un DataFrame OHLCV estándar.

        Formato de entrada confirmado:
            {
                "nextTime": "2024-11-27T00:00:00Z",
                "noData": false,
                "series": [
                    {"c": 944.0, "d": "2024-11-28T00:00:00Z", "h": 950.0,
                     "l": 937.0, "o": 940.0, "r": "D", "sid": "bm_MERV_ALUA_24hs",
                     "v": 658186.0},
                    ...
                ]
            }

        El campo "d" es un datetime UTC en formato ISO 8601. Se extrae solo la
        parte de fecha (los primeros 10 caracteres) porque el campo "d" siempre
        representa medianoche UTC, que coincide con el día de negociación.

        Args:
            raw: Body JSON parseado (ya validado por validate_response).
            ticker: Ticker del instrumento; se agrega como columna.

        Returns:
            DataFrame con columnas canónicas OHLCV_COLUMNS, ordenado por fecha.
        """
        records: list[dict] = raw["series"]

        if not records:
            logger.warning(f"[{self.source_name}] serie vacía para ticker={ticker!r}")
            return _empty_ohlcv_df(ticker)

        df = pl.DataFrame(records)

        # Renombrar campos API (o, h, l, c, v, d) → nombres canónicos.
        rename_map = {col: _API_COLUMN_MAP[col] for col in df.columns if col in _API_COLUMN_MAP}
        df = df.rename(rename_map)

        # Parsear campo "date": "2024-11-28T00:00:00Z" → date(2024, 11, 28).
        # Se toman los 10 primeros caracteres (parte de fecha) del string ISO UTC.
        df = df.with_columns(
            pl.col("date").str.slice(0, 10).str.to_date(format="%Y-%m-%d").alias("date")
        )

        # Asegurar tipos numéricos Float64 (la API los devuelve como float pero lo hacemos explícito).
        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns and df[col].dtype != pl.Float64:
                df = df.with_columns(pl.col(col).cast(pl.Float64))

        # Agregar columna ticker y seleccionar solo las columnas canónicas.
        df = df.with_columns(pl.lit(ticker).alias("ticker"))
        return df.select(OHLCV_COLUMNS).sort("date")


# ------------------------------------------------------------------ #
# Helpers a nivel módulo                                               #
# ------------------------------------------------------------------ #

def _format_date_tz(d: date) -> str:
    """Convierte una date a ISO datetime con TZ America/Argentina/Buenos_Aires.

    Las fechas se tratan como inicio del día (00:00:00) en zona horaria
    Argentina. Internamente el pipeline trabaja en UTC; la conversión a TZ
    Argentina se aplica únicamente al construir los parámetros de la API.

    Args:
        d: Fecha a formatear.

    Returns:
        String ISO 8601 con offset de TZ (ej: "2024-01-02T00:00:00-03:00").
    """
    dt = _TZ_ARGENTINA.localize(datetime(d.year, d.month, d.day))
    return dt.isoformat()


def _empty_ohlcv_df(ticker: str) -> pl.DataFrame:
    """Retorna un DataFrame vacío con el schema OHLCV canónico."""
    return pl.DataFrame(
        {
            "date": pl.Series([], dtype=pl.Date),
            "open": pl.Series([], dtype=pl.Float64),
            "high": pl.Series([], dtype=pl.Float64),
            "low": pl.Series([], dtype=pl.Float64),
            "close": pl.Series([], dtype=pl.Float64),
            "volume": pl.Series([], dtype=pl.Float64),
            "ticker": pl.Series([ticker], dtype=pl.Utf8).head(0),
        }
    )
