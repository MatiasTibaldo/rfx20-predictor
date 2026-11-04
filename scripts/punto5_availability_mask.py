"""
Punto 5, ítem 3 del feedback de los directores: esquema por ticker (variante
C: peso+retorno fijo por ticker) con codificación explícita + máscara de
disponibilidad, para habilitar SVM/DL sin imputar un valor de relleno como si
fuera una observación real.

Distinción clave respecto a la regla general del proyecto de "nunca imputar
datos reales faltantes": acá el 0 de relleno NUNCA se presenta solo — siempre
viene acompañado de la columna `{TICKER}_in_index` (1/0), que le dice
explícitamente al modelo si ese valor es una observación real o un relleno
estructural. Es el patrón estándar de "missing indicator", distinto de
imputar un valor y ocultar que falta.

Uso: uv run python scripts/punto5_availability_mask.py <stage>
  stage: build | svm | lstm | all (default: all)
"""

from __future__ import annotations

import polars as pl

from config.settings import settings
from storage.store import DuckDBStore
from scripts.prototype_component_raw_inputs import _load_base_tables, _build_ticker_variant

RESULTS_ROOT = settings.RESULTS_DIR
DATASET_NAME = "features_long_compC_masked"


def build_masked_dataset() -> None:
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name="features_long", version="v1")
    _, weighted = _load_base_tables(store)

    ticker_wr, n_tickers = _build_ticker_variant(weighted, ["weight", "log_return"], ["weight", "return"])
    tickers = sorted(weighted["ticker"].unique().to_list())

    # Flags computed BEFORE the join to features_long (so they reflect "ticker
    # absent from the index that day"), but filled AFTER it (join can also
    # introduce nulls for ~60 early train dates, 2018-04-03 to 2018-06-28,
    # before rfx20_composition.parquet's history starts — a real structural
    # gap, same semantics as "not in index" for this purpose).
    flag_exprs = [
        pl.col(f"{t}_weight").is_not_null().cast(pl.Int8).alias(f"{t}_in_index") for t in tickers
    ]
    masked = ticker_wr.with_columns(flag_exprs)

    new_cols = [c for c in masked.columns if c != "date"]
    out = df.join(masked, on="date", how="left")

    fill_exprs = (
        [pl.col(f"{t}_in_index").fill_null(0) for t in tickers]
        + [pl.col(f"{t}_{label}").fill_null(0.0) for t in tickers for label in ("weight", "return")]
    )
    out = out.with_columns(fill_exprs)

    print(f"{n_tickers} tickers, {len(new_cols)} columnas nuevas "
          f"({n_tickers} flags + {n_tickers * 2} valor), 0 nulls remanentes: "
          f"{out.select(new_cols).null_count().sum_horizontal().item() == 0}")

    store.save_parquet(out, layer="features", name=DATASET_NAME, version="v1")


def run_svm() -> None:
    from models.ml import svm_runner

    svm_runner.main(
        dataset_name=DATASET_NAME,
        results_dir=RESULTS_ROOT / "track_a_ml_compC_masked" / "svm",
    )


def run_lstm() -> None:
    from models.deep_learning import lstm_runner
    from models.deep_learning.common import FEATURE_SET_FULL

    lstm_runner.main(
        dataset_name=DATASET_NAME,
        feature_set=FEATURE_SET_FULL,
        results_dir=RESULTS_ROOT / "track_b_full_compC_masked",
    )


if __name__ == "__main__":
    import sys

    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("all", "build"):
        build_masked_dataset()
    if stage in ("all", "svm"):
        run_svm()
    if stage in ("all", "lstm"):
        run_lstm()
