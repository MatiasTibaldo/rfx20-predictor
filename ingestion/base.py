"""
Clase base abstracta para todos los conectores de datos.

Establece el contrato que deben cumplir PrimaryRESTConnector, BCRAConnector
y cualquier fuente futura. Esto garantiza que el pipeline pueda tratar todos
los conectores de forma uniforme, sin conocer su implementación interna.
"""

from abc import ABC, abstractmethod
from datetime import date

import polars as pl
from loguru import logger


class BaseConnector(ABC):
    """Interfaz común para todos los conectores de datos del pipeline RFX20.

    Cada conector es responsable de:
    - Conectarse a su fuente (API, archivo, base de datos)
    - Retornar siempre un pl.DataFrame con columnas estandarizadas
    - Validar que la respuesta recibida es utilizable

    Las implementaciones concretas no deben exponer lógica de autenticación
    ni de persistencia; eso es responsabilidad de AuthManager y DuckDBStore.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identificador legible de la fuente de datos (ej: "Primary REST API")."""
        ...

    @abstractmethod
    def fetch(self, ticker: str, date_from: date, date_to: date) -> pl.DataFrame:
        """Obtiene datos para un ticker en el rango de fechas indicado.

        Args:
            ticker: Identificador del instrumento (ej: "RFX20", "GGAL").
            date_from: Fecha de inicio del rango (inclusive).
            date_to: Fecha de fin del rango (inclusive).

        Returns:
            DataFrame con columnas estandarizadas. El conjunto mínimo de
            columnas varía por tipo de conector, pero OHLCV siempre incluye:
            ``date``, ``open``, ``high``, ``low``, ``close``, ``volume``, ``ticker``.

        Raises:
            NotImplementedError: Si la subclase no implementa este método.
            ConnectionError: Si no se puede establecer conexión con la fuente.
            ValueError: Si los parámetros son inválidos.
        """
        ...

    @abstractmethod
    def validate_response(self, response: object) -> bool:
        """Verifica que la respuesta cruda de la fuente es utilizable.

        Debe llamarse antes de parsear la respuesta para detectar errores
        semánticos (ej: respuesta vacía, campos faltantes, status de error
        embebido en el cuerpo).

        Args:
            response: Objeto de respuesta en el formato nativo del conector
                (ej: dict para REST JSON, bytes para CSV, etc.).

        Returns:
            True si la respuesta puede procesarse, False en caso contrario.
        """
        ...

    # ------------------------------------------------------------------ #
    # Helpers de logging comunes a todas las subclases                    #
    # ------------------------------------------------------------------ #

    def _log_fetch_start(self, ticker: str, date_from: date, date_to: date) -> None:
        logger.info(
            f"[{self.source_name}] fetch start | ticker={ticker!r} "
            f"from={date_from} to={date_to}"
        )

    def _log_fetch_done(self, ticker: str, rows: int) -> None:
        logger.info(f"[{self.source_name}] fetch done  | ticker={ticker!r} rows={rows:,}")

    def _log_fetch_error(self, ticker: str, error: Exception) -> None:
        logger.error(f"[{self.source_name}] fetch error | ticker={ticker!r} error={error}")
