"""
Punto 6 del feedback de los directores: barrido completo de la matriz
dataset x arquitectura x horizonte para la curva de pérdida train vs.
early-stopping (complemento a scripts/punto6_dl_diagnostics.py, que solo
cubre 3 configuraciones representativas).

A diferencia de ese script, acá el lookback no se fija a mano: se
selecciona con select_lookback() (grid search sobre LOOKBACK_CANDIDATES),
igual que en la corrida oficial — no hay un valor "ya elegido" persistido
para las 36 combinaciones, así que se re-deriva con el mismo criterio del
pipeline en vez de asumir uno.

Incluye las 9 combinaciones GRU/CNN-LSTM/TFT-lite x compC_masked que nunca
se corrieron oficialmente (docs/decisions/punto5_variantes_componentes_nov2026.md
sección 3 concluyó, solo con LSTM, que la máscara de disponibilidad "no es
útil para Deep Learning" en este proyecto) — decisión explícita de los
directores (6-nov-2026) de completar la matriz de todas formas.

Una sola semilla (42): el objetivo es ver la forma de la curva en todas las
combinaciones, no repetir el análisis de estabilidad entre semillas ya
hecho (scripts/punto6_dl_diagnostics.py) para las 3 configuraciones
originales.

Uso: uv run python scripts/punto6_dl_diagnostics_full_sweep.py
"""

from __future__ import annotations

import json

from config.settings import settings
from models.deep_learning import common as dl_common
from models.deep_learning.cnn_lstm import CNNLSTMRegressor
from models.deep_learning.common import (
    FEATURE_SET_FULL,
    HORIZONS,
    prepare_frame,
    select_lookback,
)
from models.deep_learning.gru import GRURegressor
from models.deep_learning.lstm import LSTMRegressor
from models.deep_learning.tft_lite import TFTLiteRegressor
from storage.store import DuckDBStore

RESULTS_DIR = settings.RESULTS_DIR / "punto6_dl_diagnostics_full_sweep"
SEED = 42

DATASETS = {
    "baseline": "features_long",
    "compA": "features_long_compA",
    "compC_masked": "features_long_compC_masked",
}

MODEL_SPECS = {
    "LSTM": (LSTMRegressor, {"hidden_size": 32}),
    "GRU": (GRURegressor, {"hidden_size": 32}),
    "CNN-LSTM": (CNNLSTMRegressor, {"hidden_size": 32}),
    "Transformer encoder": (TFTLiteRegressor, {"d_model": 32}),
}


def run_one(dataset_label, df, model_name, model_cls, model_kwargs, horizon):
    frame, feature_cols, target_col = prepare_frame(df, horizon=horizon, feature_set=FEATURE_SET_FULL)

    dl_common.RANDOM_STATE = SEED
    result = select_lookback(
        frame,
        feature_cols,
        target_col,
        model_factory_for_input_size=lambda n: model_cls(input_size=n, **model_kwargs),
    )

    history = result.history
    train_history = result.train_history
    best_epoch = result.best_epoch

    train_loss_best = train_history[best_epoch]
    es_loss_best = result.earlystop_loss
    train_loss_last = train_history[-1]
    es_loss_last = history[-1]
    gap_best = es_loss_best - train_loss_best
    gap_last = es_loss_last - train_loss_last

    return {
        "dataset": dataset_label,
        "model": model_name,
        "horizon": horizon,
        "lookback": result.lookback,
        "best_epoch": best_epoch,
        "n_epochs_run": len(history),
        "train_loss_first": train_history[0],
        "train_loss_best_epoch": train_loss_best,
        "train_loss_last": train_loss_last,
        "es_loss_first": history[0],
        "es_loss_best": es_loss_best,
        "es_loss_last": es_loss_last,
        "gap_best_epoch": gap_best,
        "gap_last": gap_last,
        "gap_growth": gap_last - gap_best,
        "history": history,
        "train_history": train_history,
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    store = DuckDBStore()

    all_rows = []
    for dataset_label, dataset_name in DATASETS.items():
        df = store.load_parquet(layer="features", name=dataset_name, version="v1")
        for model_name, (model_cls, model_kwargs) in MODEL_SPECS.items():
            for h in HORIZONS:
                print(f"=== {dataset_label} / {model_name} / h={h} ===", flush=True)
                r = run_one(dataset_label, df, model_name, model_cls, model_kwargs, h)
                all_rows.append(r)
                print(
                    f"  lookback={r['lookback']} best_epoch={r['best_epoch']}/{r['n_epochs_run']}  "
                    f"train {r['train_loss_first']:.5f}->{r['train_loss_best_epoch']:.5f}->{r['train_loss_last']:.5f}  "
                    f"es {r['es_loss_first']:.5f}->{r['es_loss_best']:.5f}->{r['es_loss_last']:.5f}  "
                    f"gap(best)={r['gap_best_epoch']:+.5f} gap(last)={r['gap_last']:+.5f}",
                    flush=True,
                )

    with open(RESULTS_DIR / "full_sweep.json", "w") as f:
        json.dump(all_rows, f, indent=2)

    print("\n\n===== RESUMEN: 36 combinaciones ordenadas por gap_last (mayor brecha primero) =====")
    rows_sorted = sorted(all_rows, key=lambda r: r["gap_last"], reverse=True)
    print(f"{'Dataset':<14}{'Modelo':<22}{'h':<4}{'lookback':<10}{'gap_best':<12}{'gap_last':<12}{'gap_growth':<12}")
    for r in rows_sorted:
        print(
            f"{r['dataset']:<14}{r['model']:<22}{r['horizon']:<4}{r['lookback']:<10}"
            f"{r['gap_best_epoch']:<+12.5f}{r['gap_last']:<+12.5f}{r['gap_growth']:<+12.5f}"
        )


if __name__ == "__main__":
    main()
