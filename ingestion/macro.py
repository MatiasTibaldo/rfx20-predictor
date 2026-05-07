"""
Conectores para variables macroeconómicas externas.

Estado actual: estructura lista, implementación pendiente (fetch() lanza
NotImplementedError con instrucciones sobre los endpoints a usar).

Fuentes previstas:
- BCRA API pública: https://api.bcra.gob.ar — series estadísticas del BCRA.
- INDEC: inflación mensual vía datos.gob.ar (API pública, no requiere auth).
- Dólar MEP / CCL: fuente a definir (BYMA data API, Rava, scraping).

Implementar en Fase 2 del proyecto, una vez confirmadas las fuentes definitivas
y su relevancia como features para el modelo RFX20.
"""

from datetime import date

import polars as pl
from loguru import logger

from ingestion.base import BaseConnector

# ------------------------------------------------------------------ #
# Constantes — Variables BCRA disponibles en la API pública           #
# Fuente: GET https://api.bcra.gob.ar/estadisticas/v3.0/monetarias   #
# Nota: la v3.0 usa el path /monetarias/{idVariable}, no /datosvariable
# ------------------------------------------------------------------ #

# Tipo de cambio de referencia (Com. A 3500) — dólar oficial BNA
BCRA_VAR_TIPO_CAMBIO_OFICIAL: int = 4

# Tasa BADLAR bancos privados
BCRA_VAR_BADLAR: int = 6

# Tasa de política monetaria (Tasa TAMAR / ex-LELIQ)
# LELIQ fue discontinuado en dic 2023; TAMAR lo reemplazó (id=27).
BCRA_VAR_TAMAR: int = 27

# ------------------------------------------------------------------ #
# Diccionario de variables macro a incorporar en fases posteriores    #
# ------------------------------------------------------------------ #

MACRO_VARIABLES: dict[str, str] = {
    "TIPO_CAMBIO_OFICIAL": (
        "Tipo de cambio oficial BNA (Com. A 3500). "
        "Fuente: BCRA API v3.0 /monetarias/4"
    ),
    "BADLAR": (
        "Tasa BADLAR bancos privados (promedio diario, depósitos 30-35 días). "
        "Fuente: BCRA API v3.0 /monetarias/6"
    ),
    "TAMAR": (
        "Tasa de política monetaria argentina (ex-LELIQ). "
        "Fuente: BCRA API v3.0 /monetarias/27"
    ),
    "IPC_MENSUAL": (
        "Inflación mensual IPC nacional (variación %). "
        "Fuente: datos.gob.ar — serie 148.3_INIVELNAL_DICI_M_26"
    ),
    "DOLAR_MEP": (
        "Tipo de cambio dólar MEP (electronic payment / bono AL30). "
        "Fuente: a definir (BYMA data API, Rava Bursátil, o scraping)."
    ),
    "DOLAR_CCL": (
        "Tipo de cambio dólar CCL (contado con liqui). "
        "Fuente: a definir (BYMA data API, Rava Bursátil, o scraping)."
    ),
    "EMBI_ARGENTINA": (
        "Riesgo país EMBI+ Argentina (puntos básicos). "
        "Fuente: a definir (JP Morgan via Refinitiv, o scraping ambito.com)."
    ),
}


class BCRAConnector(BaseConnector):
    """Conector para la API pública del Banco Central de la República Argentina.

    Endpoint base: https://api.bcra.gob.ar/estadisticas/v3.0/monetarias

    La API del BCRA no requiere autenticación (acceso público).
    Devuelve series diarias de variables monetarias y financieras.

    Endpoints relevantes:
        GET /estadisticas/v3.0/monetarias/{idVariable}
        Ejemplo: https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/6
        → devuelve la serie de Tasa BADLAR

        GET /estadisticas/v3.0/monetarias (sin parámetro)
        → lista todas las variables disponibles con sus IDs

    Variables clave:
        id=4  → Tipo de cambio oficial BNA (BCRA_VAR_TIPO_CAMBIO_OFICIAL)
        id=6  → Tasa BADLAR bancos privados (BCRA_VAR_BADLAR)
        id=27 → Tasa TAMAR / ex-LELIQ (BCRA_VAR_TAMAR)

    El argumento ``ticker`` se usa como identificador de variable:
    puede ser el nombre mnemónico (ej: "BADLAR") o el id numérico como string.

    Estado: estructura lista, implementación pendiente (Fase 2).
    """

    _VARIABLE_MAP: dict[str, int] = {
        "TIPO_CAMBIO": BCRA_VAR_TIPO_CAMBIO_OFICIAL,
        "BADLAR": BCRA_VAR_BADLAR,
        "TAMAR": BCRA_VAR_TAMAR,
    }

    _BASE_URL = "https://api.bcra.gob.ar"
    # Endpoint v3.0 (reemplaza v2.0 /datosvariable que fue deprecado).
    _SERIES_ENDPOINT = "/estadisticas/v3.0/monetarias/{id_variable}"

    @property
    def source_name(self) -> str:
        return "BCRA API"

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """Obtiene una serie temporal del BCRA para el período indicado.

        Args:
            ticker: Nombre mnemónico (ej: "BADLAR", "TIPO_CAMBIO") o ID numérico
                como string (ej: "6").
            date_from: Fecha de inicio (inclusive).
            date_to: Fecha de fin (inclusive).

        Returns:
            DataFrame con columnas: date (Date), value (Float64), variable (Utf8).

        TODO: Implementar en Fase 2 cuando se confirme la fuente de datos macro.

        Notas de implementación:
            - La API del BCRA tiene rate limiting no documentado; agregar sleep entre
              requests si se descargan múltiples variables en secuencia.
            - Los feriados argentinos producen gaps en la serie (no interpolar aquí;
              esa responsabilidad es del módulo features/).
            - Algunos valores históricos tienen correcciones retroactivas; la API
              siempre devuelve la última versión disponible.
            - La respuesta tiene formato:
              {"status": 200, "results": [{"fecha": "2024-01-02", "valor": 123.45}, ...]}
        """
        self._log_fetch_start(ticker, date_from, date_to)
        raise NotImplementedError(
            f"BCRAConnector.fetch() no implementado (Fase 2). "
            f"Usar: GET {self._BASE_URL}{self._SERIES_ENDPOINT.format(id_variable='<id>')}. "
            f"Variable solicitada: {ticker!r}. "
            f"Ver constantes BCRA_VAR_* y MACRO_VARIABLES en este módulo."
        )

    def validate_response(self, response: object) -> bool:
        """Verifica que la respuesta del BCRA tiene el formato esperado.

        TODO: Implementar junto con fetch() en Fase 2.
        La API del BCRA devuelve {"status": 200, "results": [...]}.
        Validar que status == 200 y results es una lista no vacía.
        """
        raise NotImplementedError("BCRAConnector.validate_response() no implementado (Fase 2).")

    def _resolve_variable_id(self, ticker: str) -> int:
        """Convierte un mnemónico o ID como string al ID numérico del BCRA.

        Args:
            ticker: Nombre mnemónico o ID numérico como string.

        Returns:
            ID entero de la variable BCRA.

        Raises:
            ValueError: Si el ticker no se reconoce ni es un entero válido.
        """
        if ticker in self._VARIABLE_MAP:
            return self._VARIABLE_MAP[ticker]
        try:
            return int(ticker)
        except ValueError:
            raise ValueError(
                f"Variable BCRA desconocida: {ticker!r}. "
                f"Opciones: {list(self._VARIABLE_MAP.keys())} "
                f"o usar el ID numérico como string (ej: '6')."
            )


class INDECConnector(BaseConnector):
    """Placeholder para inflación mensual del INDEC vía datos.gob.ar.

    API pública (no requiere auth):
        https://apis.datos.gob.ar/series/api/series/?ids={serie_id}&format=json

    Serie IPC nacional (variación mensual):
        ID: 148.3_INIVELNAL_DICI_M_26

    Estado: no implementado. Requiere confirmar fuente definitiva (Fase 2).
    """

    _BASE_URL = "https://apis.datos.gob.ar/series/api"
    _SERIES_ID_IPC = "148.3_INIVELNAL_DICI_M_26"

    @property
    def source_name(self) -> str:
        return "INDEC (datos.gob.ar)"

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """TODO: Implementar en Fase 2 cuando se confirme uso de inflación como feature.

        Endpoint:
            GET {_BASE_URL}/series/?ids={_SERIES_ID_IPC}&start_date={date_from}&end_date={date_to}
        """
        self._log_fetch_start(ticker, date_from, date_to)
        raise NotImplementedError(
            "INDECConnector.fetch() no implementado (Fase 2). "
            f"Endpoint: {self._BASE_URL}/series/?ids={self._SERIES_ID_IPC}"
        )

    def validate_response(self, response: object) -> bool:
        """TODO: Implementar junto con fetch() en Fase 2."""
        raise NotImplementedError("INDECConnector.validate_response() no implementado (Fase 2).")


class DolarMEPConnector(BaseConnector):
    """Placeholder para datos de dólar MEP (electronic payment) y CCL.

    Fuentes candidatas (a confirmar en Fase 2):
    - BYMA data API (acceso via Primary / MatbaRofex)
    - Rava Bursátil API pública
    - Scraping de Mercado Abierto Electrónico (MAE)
    - IOL (Invertir Online) API

    El dólar MEP se calcula operando bono AL30 o GD30 en pesos y dólares.
    El CCL (contado con liqui) involucra transferencia al exterior.

    Estado: no implementado. Fuente a definir en Fase 2.
    """

    @property
    def source_name(self) -> str:
        return "Dólar MEP/CCL (fuente a definir)"

    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """TODO: Implementar en Fase 2 cuando se confirme la fuente de datos.

        Args:
            ticker: "MEP" o "CCL" para indicar el tipo de cotización.
        """
        self._log_fetch_start(ticker, date_from, date_to)
        raise NotImplementedError(
            "DolarMEPConnector.fetch() no implementado (Fase 2). "
            "Fuente de datos pendiente de definición. "
            "Ver MACRO_VARIABLES['DOLAR_MEP'] para candidatos."
        )

    def validate_response(self, response: object) -> bool:
        """TODO: Implementar junto con fetch() en Fase 2."""
        raise NotImplementedError(
            "DolarMEPConnector.validate_response() no implementado (Fase 2)."
        )
