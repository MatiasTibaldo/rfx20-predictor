"""
Exploratorio (no es un nodo del pipeline): construye una variante de
features_long con horizontes largos (10/21 días hábiles, ~2 semanas / 1 mes)
sumados a los ya existentes 1/3/5, para evaluar si Track A encuentra señal
en horizontes intermedios que no encontró en el corto plazo — ver
docs/decisions/long_horizons_track_a.md.

Deliberadamente NO sobreescribe data/features/v1/features_long.parquet
(el dataset canónico ya validado y commiteado): persiste aparte, en
data/features/v1/features_long_ext.parquet, para poder descartar este
experimento sin tocar nada de lo ya cerrado si no da resultados.

Reusa el macro.parquet ya persistido (el calendario del índice no cambia
al sumar horizontes, solo se agregan columnas de target) — no vuelve a
pegarle a las fuentes de futuros/macro.

Uso: uv run python -m scripts.build_features_long_extended
"""

from __future__ import annotations

from loguru import logger

from features.consolidate import build_features_long
from features.target import build_index_target
from features.technical import add_technical_indicators
from features.volatility import add_realized_volatility
from storage.store import DuckDBStore

HORIZONS = [1, 3, 5, 10, 21]
MA_WINDOWS = [10, 20, 50]


def main() -> None:
    store = DuckDBStore()

    spot_df = store.load_parquet(layer="raw", name="rfx20_spot", version="v1")
    index_df = build_index_target(spot_df, HORIZONS)
    index_df = add_technical_indicators(index_df, MA_WINDOWS)
    index_df = add_realized_volatility(index_df, MA_WINDOWS)

    macro_df = store.load_parquet(layer="features", name="macro", version="v1")

    features_long_ext = build_features_long(index_df, macro_df)
    logger.info(
        f"[build_features_long_extended] {features_long_ext.height:,} filas, "
        f"{len(features_long_ext.columns)} columnas, horizontes={HORIZONS}"
    )

    store.save_parquet(
        features_long_ext,
        layer="features",
        name="features_long_ext",
        version="v1",
        also_csv=True,
    )


if __name__ == "__main__":
    main()
