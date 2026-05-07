"""
ingestion — Adquisición de datos crudos para el pipeline RFX20.

Responsabilidades:
- Conectar con la API REST de Primary S.A. (Matriz xoms) para series OHLCV históricas.
- Gestionar autenticación por cookie de sesión (flujo CSRF, renovación automática ante 401).
- Mapear tickers MERVAL a instrument_ids del formato de la API.
- Obtener variables macroeconómicas de fuentes externas (BCRA, INDEC) — Fase 2.
- Persistir todos los datos en data/raw/ via DuckDBStore.

Módulos:
    base.py         — BaseConnector: clase abstracta común a todos los conectores.
    auth.py         — AuthManager: login CSRF y ciclo de vida de la cookie de sesión.
    instruments.py  — Mapeo ticker ↔ instrument_id + lista RFX20_TICKERS.
    primary_rest.py — PrimaryRESTConnector: OHLCV diario histórico vía REST v2.
    macro.py        — BCRAConnector, INDECConnector, DolarMEPConnector (Fase 2).
    pipeline.py     — IngestionPipeline: orquestador de la ingesta completa.

Uso típico:
    >>> from ingestion.pipeline import IngestionPipeline
    >>> from datetime import date
    >>> pipeline = IngestionPipeline()
    >>> results = pipeline.run_rfx20(date(2020, 1, 1), date(2024, 12, 31))
    >>> failed = [t for t, ok in results.items() if not ok]
"""

from ingestion.auth import AuthError, AuthManager
from ingestion.base import BaseConnector
from ingestion.instruments import (
    RESOLUTION_DAILY,
    RFX20_TICKERS,
    instrument_id_to_ticker,
    ticker_to_instrument_id,
)
from ingestion.pipeline import IngestionPipeline
from ingestion.primary_rest import PrimaryRESTConnector

__all__ = [
    "AuthError",
    "AuthManager",
    "BaseConnector",
    "IngestionPipeline",
    "PrimaryRESTConnector",
    "RESOLUTION_DAILY",
    "RFX20_TICKERS",
    "instrument_id_to_ticker",
    "ticker_to_instrument_id",
]
