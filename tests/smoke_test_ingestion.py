"""
Smoke test de integración para el módulo ingestion/.

Verifica el flujo completo contra la API real de Primary S.A.:
    1. Login (flujo CSRF → cookie de sesión)
    2. Fetch OHLCV de ALUA para Q1 2025

No guarda nada en disco. Ejecutar con credenciales reales en .env.

Uso:
    python tests/smoke_test_ingestion.py
    uv run python tests/smoke_test_ingestion.py
"""

import sys
from datetime import date
from pathlib import Path

# Asegurar que el proyecto está en el path cuando se corre directamente.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from config.settings import settings
from ingestion.auth import AuthError, AuthManager
from ingestion.primary_rest import PrimaryRESTConnector

# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def _fail(msg: str) -> None:
    logger.error(f"SMOKE TEST FAILED — {msg}")
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Paso 1: configuración                                                         #
# --------------------------------------------------------------------------- #

logger.info("=" * 60)
logger.info("SMOKE TEST — ingestion/")
logger.info("=" * 60)

logger.info(f"PRIMARY_BASE_URL = {settings.PRIMARY_BASE_URL!r}")

if not settings.PRIMARY_BASE_URL:
    _fail("PRIMARY_BASE_URL está vacío. Verificar .env")
if not settings.PRIMARY_USER:
    _fail("PRIMARY_USER está vacío. Verificar .env")
if not settings.PRIMARY_PASS:
    _fail("PRIMARY_PASS está vacío. Verificar .env")

# --------------------------------------------------------------------------- #
# Paso 2: login                                                                 #
# --------------------------------------------------------------------------- #

logger.info("[Paso 2] Instanciando AuthManager y llamando login()…")

auth = AuthManager()

try:
    auth.login()
except AuthError as exc:
    _fail(f"AuthError durante login: {exc}")
except ValueError as exc:
    _fail(f"Configuración inválida: {exc}")
except Exception as exc:
    _fail(f"Error inesperado durante login: {type(exc).__name__}: {exc}")

logger.info("[Paso 2] Login OK — sesión activa.")

# --------------------------------------------------------------------------- #
# Paso 3: fetch OHLCV                                                           #
# --------------------------------------------------------------------------- #

TICKER = "ALUA"
DATE_FROM = date(2025, 1, 1)
DATE_TO = date(2025, 3, 31)

logger.info(f"[Paso 3] Fetch OHLCV | ticker={TICKER!r} from={DATE_FROM} to={DATE_TO}")

connector = PrimaryRESTConnector(auth_manager=auth)

try:
    df = connector.fetch(TICKER, DATE_FROM, DATE_TO)
except AuthError as exc:
    _fail(f"AuthError durante fetch: {exc}")
except ConnectionError as exc:
    _fail(f"Error de conexión durante fetch: {exc}")
except ValueError as exc:
    _fail(f"Respuesta inválida de la API: {exc}")
except Exception as exc:
    _fail(f"Error inesperado durante fetch: {type(exc).__name__}: {exc}")

logger.info(f"[Paso 3] Fetch OK — shape=({len(df)} filas × {len(df.columns)} columnas)")
logger.info(f"[Paso 3] Columnas: {df.columns}")

if df.is_empty():
    logger.warning("[Paso 3] DataFrame vacío — la API no devolvió datos para el período.")
else:
    logger.info("[Paso 3] Primeras 3 filas:")
    print(df.head(3))

# --------------------------------------------------------------------------- #
# Resultado final                                                               #
# --------------------------------------------------------------------------- #

logger.info("=" * 60)
logger.info("SMOKE TEST PASSED")
logger.info("=" * 60)
