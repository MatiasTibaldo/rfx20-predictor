"""
Exploración de diferenciación fraccional sobre el log-precio del índice RFX20.

Nodo 4, Etapa 3 (tarea 4 del plan de acción: "exploración acotada, no
bloqueante"). Script manual — no es un nodo del pipeline de Streamlit, se
corre a demanda (mismo patrón que validate_variation.py y
fetch_rfx20_futures.py).

Implementa Fixed-Width Window Fracdiff (FFD), López de Prado —
"Advances in Financial Machine Learning", cap. 5 — a mano (sin agregar una
dependencia nueva como el paquete `fracdiff` para un análisis exploratorio
que puede no volver a correrse). Si el hallazgo justifica productivizarlo
como feature real (Track A de Bloque 2, modelos ARIMA/SARIMA), ahí se
evalúa si conviene migrar a una implementación vectorizada de terceros.

Método:
    1. Para cada d en la grilla, calcular los pesos de FFD (decaen hasta
       cruzar el umbral `thres`, fijando el ancho de la ventana).
    2. Aplicar la ventana como suma ponderada rodante sobre log(close).
    3. Test ADF (statsmodels) sobre la serie resultante — estacionariedad.
    4. Correlación de Pearson con la serie original — memoria conservada.
    5. Reportar el d mínimo que ya rechaza la hipótesis de raíz unitaria
       (ADF p-value < 0.05), el que maximiza memoria dentro de los
       estacionarios.

Uso:
    uv run python -m scripts.fractional_diff_exploration
"""

from __future__ import annotations

import numpy as np
import polars as pl
from loguru import logger
from statsmodels.tsa.stattools import adfuller

from storage.store import DuckDBStore

_D_GRID = [round(d, 2) for d in np.arange(0.0, 1.01, 0.05)]
_THRESHOLD = 1e-5
_ADF_ALPHA = 0.05


def get_weights_ffd(d: float, thres: float = _THRESHOLD) -> np.ndarray:
    """Compute Fixed-Width Window Fracdiff weights for order ``d``.

    Weights follow w_0 = 1, w_k = -w_{k-1} * (d - k + 1) / k, truncated
    once |w_k| drops below ``thres`` — this fixes the window width instead
    of letting it grow with the series length (expanding-window fracdiff),
    which keeps the weights numerically stable.

    Args:
        d: Fractional differentiation order, in [0, 1] for this exploration
            (0 = raw series, 1 = full difference / standard log-return).
        thres: Weight-magnitude cutoff that determines the window width.

    Returns:
        1-D array of weights, ordered from most recent (index 0) to oldest.
    """
    weights = [1.0]
    k = 1
    while True:
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < thres:
            break
        weights.append(w_k)
        k += 1
    return np.array(weights)


def frac_diff_ffd(series: pl.Series, d: float, thres: float = _THRESHOLD) -> pl.Series:
    """Apply Fixed-Width Window Fracdiff to a series.

    Args:
        series: Input series (e.g. log-price), assumed already sorted by
            date with no gaps.
        d: Fractional differentiation order.
        thres: Forwarded to :func:`get_weights_ffd`.

    Returns:
        Series of the same length. The first ``len(weights) - 1`` values
        are null (insufficient history for the fixed window), matching the
        warm-up convention already used for rolling indicators in
        ``features/technical.py`` / ``features/volatility.py``.
    """
    weights = get_weights_ffd(d, thres)
    window = len(weights)
    values = series.to_numpy()
    n = len(values)

    out = np.full(n, np.nan)
    for t in range(window - 1, n):
        out[t] = np.dot(weights, values[t - window + 1 : t + 1][::-1])

    return pl.Series(series.name, out)


def run_exploration(log_price: pl.Series) -> pl.DataFrame:
    """Sweep the d grid and report stationarity / memory trade-offs.

    Args:
        log_price: Log-price series of the RFX20 index, sorted by date.

    Returns:
        DataFrame with one row per d: window width, ADF statistic,
        ADF p-value, and Pearson correlation with the original series
        (computed over the overlapping non-null window).
    """
    original_np = log_price.to_numpy()
    rows = []
    for d in _D_GRID:
        diffed_np = frac_diff_ffd(log_price, d).to_numpy()
        # NaN (warm-up) is not the same as polars null — filter in numpy
        # space with isfinite instead of relying on null-aware methods
        # (same pitfall documented for the `ta` indicators warm-up).
        valid_mask = np.isfinite(diffed_np)
        valid = diffed_np[valid_mask]
        original_valid = original_np[valid_mask]

        window = len(get_weights_ffd(d))
        adf_stat, adf_pvalue = np.nan, np.nan
        corr = np.nan
        if window >= len(original_np):
            logger.warning(
                f"[fracdiff] d={d:.2f} requiere ventana de {window} ruedas, "
                f"mayor a las {len(original_np)} disponibles — se omite."
            )
        elif len(valid) > 20:
            adf_result = adfuller(valid, autolag="AIC")
            adf_stat, adf_pvalue = adf_result[0], adf_result[1]
            corr = float(np.corrcoef(valid, original_valid)[0, 1])

        rows.append(
            {
                "d": d,
                "window": window,
                "n_valid": len(valid),
                "adf_stat": adf_stat,
                "adf_pvalue": adf_pvalue,
                "stationary": bool(adf_pvalue < _ADF_ALPHA) if not np.isnan(adf_pvalue) else False,
                "corr_with_original": corr,
            }
        )
        logger.info(
            f"[fracdiff] d={d:.2f} window={rows[-1]['window']:>4} "
            f"ADF p={adf_pvalue:.4f} stationary={rows[-1]['stationary']} "
            f"corr={corr:.4f}"
        )

    return pl.DataFrame(rows)


def main() -> None:
    store = DuckDBStore()
    idx = store.load_parquet(layer="features", name="technical_index", version="v1").sort("date")
    log_price = idx["close"].log()
    log_price = pl.Series("log_close", log_price.to_numpy())

    logger.info(
        f"[fracdiff] Exploring d in [{_D_GRID[0]}, {_D_GRID[-1]}] "
        f"({len(_D_GRID)} steps) over {len(log_price):,} rows of log(close)."
    )
    results = run_exploration(log_price)

    stationary = results.filter(pl.col("stationary"))
    if stationary.height == 0:
        logger.warning("[fracdiff] Ningún d de la grilla logra estacionariedad (p < 0.05).")
    else:
        d_min = stationary.sort("d").row(0, named=True)
        logger.info(
            f"[fracdiff] d mínimo estacionario: d={d_min['d']:.2f} "
            f"(ADF p={d_min['adf_pvalue']:.4f}, corr={d_min['corr_with_original']:.4f}, "
            f"ventana={d_min['window']} ruedas)"
        )

    print(results)


if __name__ == "__main__":
    main()
