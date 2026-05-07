"""
Orquestador del módulo de ingestion.

Coordina autenticación, fetch por ticker y persistencia en raw/ via DuckDBStore.
El pipeline es tolerante a fallos por ticker: si uno falla, los restantes
continúan. Esto es deliberado — en un run de 20 tickers no queremos perder
los 19 exitosos por un problema puntual.

Contrato de salida (hacia el módulo features):
    Parquet en data/raw/{version}/{ticker}_ohlcv.parquet
    (vía DuckDBStore.save_parquet con layer="raw")
"""

from __future__ import annotations

from datetime import date

from loguru import logger

from ingestion.auth import AuthError, AuthManager
from ingestion.instruments import RFX20_TICKERS
from ingestion.primary_rest import PrimaryRESTConnector
from storage.store import DuckDBStore


class IngestionPipeline:
    """Orquesta la ingesta de datos OHLCV históricos desde Primary S.A.

    Instancia AuthManager y PrimaryRESTConnector internamente con defaults
    de settings. Se puede inyectar un conector custom para testing.

    Responsabilidades:
    - Iterar sobre la lista de tickers y persistir cada uno en raw/.
    - Registrar éxitos y fallos sin interrumpir la ejecución.
    - Retornar un diccionario {ticker: success} para auditoría del llamador.

    Args:
        store: Instancia de DuckDBStore. Si se omite, se crea una con defaults.
        connector: Conector OHLCV. Si se omite, se crea PrimaryRESTConnector
            con un AuthManager desde settings. Inyectar un mock en tests.

    Example:
        >>> pipeline = IngestionPipeline()
        >>> results = pipeline.run_rfx20(date(2020, 1, 1), date(2024, 12, 31))
        >>> failed = [t for t, ok in results.items() if not ok]
    """

    def __init__(
        self,
        store: DuckDBStore | None = None,
        connector: PrimaryRESTConnector | None = None,
    ) -> None:
        self._store = store or DuckDBStore()
        self._connector = connector or PrimaryRESTConnector(auth_manager=AuthManager())

    # ------------------------------------------------------------------ #
    # Interfaz pública                                                     #
    # ------------------------------------------------------------------ #

    def run(
        self,
        tickers: list[str],
        date_from: date,
        date_to: date,
        version: str = "v1",
    ) -> dict[str, bool]:
        """Ejecuta la ingesta OHLCV para una lista de tickers.

        Para cada ticker:
        1. fetch OHLCV via PrimaryRESTConnector.
        2. Guardado en raw/ via DuckDBStore.save_parquet.
        3. Un ticker fallido → log de error → continúa con el siguiente.

        Args:
            tickers: Lista de símbolos (ej: ["ALUA", "GGAL"]).
            date_from: Inicio del período histórico a descargar.
            date_to: Fin del período histórico a descargar.
            version: Versión de los archivos Parquet (ej: "v1").

        Returns:
            Dict {ticker: True/False} — True si el ticker se procesó correctamente.

        Raises:
            ValueError: Si tickers está vacío o las fechas son inválidas.
        """
        if not tickers:
            raise ValueError("La lista de tickers no puede estar vacía.")
        if date_from > date_to:
            raise ValueError(
                f"date_from ({date_from}) debe ser anterior a date_to ({date_to})."
            )

        logger.info(
            f"[IngestionPipeline] Iniciando run | tickers={len(tickers)} "
            f"from={date_from} to={date_to} version={version!r}"
        )

        results: dict[str, bool] = {}
        for i, ticker in enumerate(tickers, start=1):
            logger.info(f"[IngestionPipeline] [{i}/{len(tickers)}] Procesando {ticker!r}…")
            results[ticker] = self._process_ticker(ticker, date_from, date_to, version)

        ok = sum(results.values())
        failed = len(results) - ok
        logger.info(
            f"[IngestionPipeline] Run finalizado | exitosos={ok} fallidos={failed} "
            f"total={len(results)}"
        )
        if failed:
            failed_tickers = [t for t, success in results.items() if not success]
            logger.warning(f"[IngestionPipeline] Tickers con error: {failed_tickers}")

        return results

    def run_rfx20(
        self,
        date_from: date,
        date_to: date,
        version: str = "v1",
    ) -> dict[str, bool]:
        """Ejecuta la ingesta OHLCV para los 20 tickers del índice RFX20.

        Wrapper de conveniencia que llama run() con RFX20_TICKERS completo.

        Args:
            date_from: Inicio del período histórico.
            date_to: Fin del período histórico.
            version: Versión de los archivos Parquet (ej: "v1").

        Returns:
            Dict {ticker: True/False} con el resultado de cada ticker.
        """
        logger.info(
            f"[IngestionPipeline] Iniciando run RFX20 completo "
            f"({len(RFX20_TICKERS)} tickers)"
        )
        return self.run(RFX20_TICKERS, date_from, date_to, version)

    def run_macro(self) -> None:
        """Placeholder para integración futura de fuentes macroeconómicas.

        Cuando BCRAConnector, INDECConnector y DolarMEPConnector estén
        implementados, este método orquestará su ejecución y persistirá
        los resultados en raw/macro/.

        TODO: Implementar en Fase 2. Ver ingestion/macro.py para el diseño
              de los conectores y MACRO_VARIABLES para las series a descargar.
        """
        raise NotImplementedError(
            "IngestionPipeline.run_macro() no implementado (Fase 2). "
            "Requiere definir las fuentes de datos macro. "
            "Ver CLAUDE.md → 'Decisiones a confirmar' y ingestion/macro.py."
        )

    # ------------------------------------------------------------------ #
    # Helpers privados                                                     #
    # ------------------------------------------------------------------ #

    def _process_ticker(
        self, ticker: str, date_from: date, date_to: date, version: str
    ) -> bool:
        """Fetch + persistencia para un ticker individual.

        Captura todas las excepciones para que el pipeline pueda continuar
        con el siguiente ticker. Solo propaga AuthError irrecuperable como
        advertencia (pero igual continúa — el AuthManager intentará renovar
        la sesión en el próximo fetch).

        Args:
            ticker: Símbolo del instrumento.
            date_from: Inicio del período.
            date_to: Fin del período.
            version: Versión del Parquet de salida.

        Returns:
            True si el ticker se procesó y guardó correctamente, False si falló.
        """
        # Checkpoint: verificar en disco ANTES de cualquier request HTTP.
        # get_client() (y por ende login()) solo se invoca si llegamos al fetch().
        dataset_name = f"{ticker.lower()}_ohlcv"
        if self._store.parquet_exists("raw", dataset_name, version):
            logger.info(f"[IngestionPipeline] {ticker!r}: skip — ya descargado.")
            return True

        try:
            df = self._connector.fetch(ticker, date_from, date_to)

            if df.is_empty():
                logger.warning(
                    f"[IngestionPipeline] {ticker!r}: 0 filas guardadas "
                    f"(sin datos en el rango {date_from} → {date_to})."
                )
                return True

            self._store.save_parquet(df, layer="raw", name=dataset_name, version=version)
            return True

        except AuthError as exc:
            logger.error(f"[IngestionPipeline] {ticker!r}: error de auth — {exc}")
            return False

        except Exception as exc:
            logger.error(f"[IngestionPipeline] {ticker!r}: error inesperado — {exc}")
            return False
