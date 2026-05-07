"""
Mapeo de tickers del índice RFX20 a instrument_ids de la API Primary.

La API de Primary (Matba Rofex / xoms) identifica los instrumentos con el formato:
    bm_MERV_{TICKER}_24hs
donde TICKER es el símbolo del instrumento en MERVAL (ej: ALUA, GGAL, YPFD).

Este módulo centraliza la conversión para que cualquier cambio en la convención
de nombres de la API solo requiera modificar este archivo.
"""

# Componentes del índice RFX20 (20 acciones líderes del MERVAL).
# Completar / actualizar según la composición vigente del índice.
RFX20_TICKERS: list[str] = ['AGRO', 'ALUA', 'APBR', 'BBAR', 'BMA', 'BYMA', 'CEPU', 'COME', 'CRES', 'CVH', 'EDN', 'GGAL', 'IRSA', 'LOMA', 'METR', 'MIRG', 'MORI', 'PAMP', 'SUPV', 'TECO2', 'TGNO4', 'TGSU2', 'TRAN', 'TS', 'TXAR', 'VALO', 'YPFD']


# Resolución temporal diaria que acepta la API de Primary.
RESOLUTION_DAILY: str = "D"

# Prefijo y sufijo del formato de instrument_id de Primary.
_ID_PREFIX = "bm_MERV_"
_ID_SUFFIX = "_24hs"


def ticker_to_instrument_id(ticker: str) -> str:
    """Convierte un ticker de MERVAL al instrument_id que usa la API de Primary.

    Args:
        ticker: Símbolo del instrumento (ej: "ALUA", "GGAL", "YPFD").

    Returns:
        Instrument ID en formato bm_MERV_{ticker}_24hs.

    Example:
        >>> ticker_to_instrument_id("ALUA")
        'bm_MERV_ALUA_24hs'
    """
    return f"{_ID_PREFIX}{ticker}{_ID_SUFFIX}"


def instrument_id_to_ticker(instrument_id: str) -> str:
    """Extrae el ticker de un instrument_id de la API de Primary.

    Operación inversa de ticker_to_instrument_id. Útil al parsear respuestas
    de la API que devuelven el instrument_id en lugar del ticker.

    Args:
        instrument_id: Identificador en formato bm_MERV_{TICKER}_24hs.

    Returns:
        Símbolo del instrumento (ej: "ALUA").

    Raises:
        ValueError: Si el instrument_id no tiene el formato esperado.

    Example:
        >>> instrument_id_to_ticker("bm_MERV_ALUA_24hs")
        'ALUA'
    """
    if not instrument_id.startswith(_ID_PREFIX) or not instrument_id.endswith(_ID_SUFFIX):
        raise ValueError(
            f"Formato de instrument_id inválido: {instrument_id!r}. "
            f"Formato esperado: {_ID_PREFIX}{{TICKER}}{_ID_SUFFIX}"
        )
    return instrument_id[len(_ID_PREFIX) : -len(_ID_SUFFIX)]
