"""
Funciones de fetch para composición y divisor del RFX20 (WS de MatbaRofex).

Mismo host que ingestion/rfx20_index.py (mismo problema de cadena TLS
incompleta, mismo tratamiento: verify=False documentado). A diferencia del
endpoint de spot (/index), estos tres no aceptan rango de fechas — /historical
y /divisor son de una fecha por llamada, así que un backfill sobre varios
días hace un request por fecha por endpoint (ver
scripts/backfill_rfx20_composition.py).

Endpoints:
    GET /api/rfx20                    — snapshot actual: cartera vigente +
                                         proyectada + histórica de "hoy"
    GET /api/rfx20/historical?date=X  — composición + precio por instrumento
                                         en la fecha X (equivalente a un
                                         archivo de Cartera Historica)
    GET /api/rfx20/divisor?date=X     — divisor vigente en la fecha X
"""

from __future__ import annotations

from datetime import date

import httpx
import polars as pl
from loguru import logger
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

_BASE_URL = "https://ws.matbarofex.com.ar:8999"
_TIMEOUT = 30
_MAX_RETRIES = 3


def _get(client: httpx.Client, url: str, params: dict | None = None) -> dict | list:
    for attempt in Retrying(
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.RequestError, ConnectionError)),
        reraise=True,
    ):
        with attempt:
            try:
                response = client.get(url, params=params)
            except httpx.TimeoutException as exc:
                raise httpx.RequestError(f"Timeout ({_TIMEOUT}s) al conectar con {url}") from exc
            if response.is_server_error:
                raise ConnectionError(f"HTTP {response.status_code} — {response.text[:200]}")
            response.raise_for_status()
            return response.json()

    raise ConnectionError(f"No se pudo completar el request a {url}")  # pragma: no cover


def fetch_snapshot(client: httpx.Client | None = None) -> dict:
    """GET /api/rfx20 — cartera vigente + proyectada + histórica de "hoy".

    Returns:
        Dict con claves ``current`` (vigente + divisor), ``projected``
        (proyectada) e ``historic`` (histórica de la fecha más reciente).
    """
    own_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT, verify=False)
    try:
        return _get(client, f"{_BASE_URL}/api/rfx20")
    finally:
        if own_client:
            client.close()


def fetch_historical(target_date: date, client: httpx.Client | None = None) -> pl.DataFrame:
    """GET /api/rfx20/historical?date=X — composición + precio por instrumento.

    Args:
        target_date: Fecha a consultar.
        client: Cliente httpx reutilizable (para backfills de muchas fechas).

    Returns:
        DataFrame con columnas ``ticker``, ``cantidades_vigentes``, ``close``,
        ``fecha_cantidades_vigentes``, ``fecha_precio`` — mismo esquema que
        los archivos de Cartera Historica existentes.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT, verify=False)
    try:
        raw = _get(client, f"{_BASE_URL}/api/rfx20/historical", {"date": target_date.isoformat()})
    finally:
        if own_client:
            client.close()

    if not isinstance(raw, list) or not raw:
        logger.warning(f"[rfx20_composition_ws] /historical sin datos para {target_date}")
        return pl.DataFrame(
            schema={
                "ticker": pl.Utf8, "cantidades_vigentes": pl.Float64, "close": pl.Float64,
                "fecha_cantidades_vigentes": pl.Utf8, "fecha_precio": pl.Utf8,
            }
        )

    df = pl.DataFrame(raw)
    return df.select(
        pl.col("ticker"),
        pl.col("size").alias("cantidades_vigentes"),
        pl.col("price").alias("close"),
        pl.col("date_size").str.slice(0, 10).alias("fecha_cantidades_vigentes"),
        pl.col("date_price").str.slice(0, 10).alias("fecha_precio"),
    )


def fetch_divisor(target_date: date, client: httpx.Client | None = None) -> float | None:
    """GET /api/rfx20/divisor?date=X — divisor vigente en la fecha X.

    Args:
        target_date: Fecha a consultar.
        client: Cliente httpx reutilizable.

    Returns:
        Valor del divisor, o None si el endpoint no devolvió dato para
        esa fecha.
    """
    own_client = client is None
    client = client or httpx.Client(timeout=_TIMEOUT, verify=False)
    try:
        raw = _get(client, f"{_BASE_URL}/api/rfx20/divisor", {"date": target_date.isoformat()})
    finally:
        if own_client:
            client.close()

    if not isinstance(raw, dict) or "divisor" not in raw:
        logger.warning(f"[rfx20_composition_ws] /divisor sin datos para {target_date}")
        return None
    return float(raw["divisor"])
