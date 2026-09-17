"""
Carga unificada de las predicciones de validación de todos los modelos de
Bloque 2 (Track A + Track B) para visualización — usado tanto por las
figuras estáticas (evaluation/figures.py) como por la sección "Modelos"
del dashboard de Streamlit (app.py), para no duplicar la lógica de "qué
archivos existen y cómo se leen" en dos lugares.

Cada familia de modelos persistió sus predicciones con una convención de
nombres levemente distinta (evolucionaron en sesiones separadas —
ARIMA/GARCH en un solo parquet combinado con columna `horizon`; Track A ML
y Track B en un parquet por horizonte) — MODEL_REGISTRY encapsula esa
heterogeneidad para que el resto del código trabaje siempre con el mismo
esquema largo: (model, label, family, feature_set, horizon, date, y_true,
y_pred).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl
from loguru import logger

from config.settings import settings
from models.ml.common import HORIZONS, naive_zero_metrics
from storage.store import DuckDBStore

RESULTS_DIR = settings.RESULTS_DIR
TRACK_A_STAT_DIR = RESULTS_DIR / "track_a"
TRACK_A_ML_DIR = RESULTS_DIR / "track_a_ml"
TRACK_B_DIR = RESULTS_DIR / "track_b"

TRACK_A_ESTADISTICO = "Track A — Estadístico"
TRACK_A_ML = "Track A — ML clásico"
TRACK_B_DL = "Track B — Deep Learning"


@dataclass(frozen=True)
class ModelSpec:
    model: str
    label: str
    family: str
    feature_set: str
    combined_path: Path | None = None  # un solo archivo con columna "horizon"
    path_template: str | None = None  # "{h}" se reemplaza por el horizonte


MODEL_REGISTRY: list[ModelSpec] = [
    ModelSpec(
        "arima", "ARIMA/SARIMA", TRACK_A_ESTADISTICO, "narrow",
        combined_path=TRACK_A_STAT_DIR / "arima_val_predictions.parquet",
    ),
    ModelSpec(
        "svm", "SVM", TRACK_A_ML, "narrow",
        path_template=str(TRACK_A_ML_DIR / "svm" / "svm_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "rf", "Random Forest", TRACK_A_ML, "narrow",
        path_template=str(TRACK_A_ML_DIR / "rf" / "rf_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "xgboost", "XGBoost", TRACK_A_ML, "narrow",
        path_template=str(TRACK_A_ML_DIR / "xgboost" / "xgboost_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "lightgbm", "LightGBM", TRACK_A_ML, "narrow",
        path_template=str(TRACK_A_ML_DIR / "lightgbm" / "lightgbm_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "lstm", "LSTM", TRACK_B_DL, "narrow",
        path_template=str(TRACK_B_DIR / "lstm_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "lstm_full", "LSTM (features completos)", TRACK_B_DL, "full",
        path_template=str(TRACK_B_DIR / "lstm_val_predictions_h{h}_full.parquet"),
    ),
    ModelSpec(
        "gru", "GRU", TRACK_B_DL, "narrow",
        path_template=str(TRACK_B_DIR / "gru_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "gru_full", "GRU (features completos)", TRACK_B_DL, "full",
        path_template=str(TRACK_B_DIR / "gru_val_predictions_h{h}_full.parquet"),
    ),
    ModelSpec(
        "cnn_lstm", "CNN-LSTM", TRACK_B_DL, "narrow",
        path_template=str(TRACK_B_DIR / "cnn_lstm_val_predictions_h{h}.parquet"),
    ),
    ModelSpec(
        "tft_lite", "TFT-lite", TRACK_B_DL, "narrow",
        path_template=str(TRACK_B_DIR / "tft_lite_val_predictions_h{h}.parquet"),
    ),
]

GARCH_PATH = TRACK_A_STAT_DIR / "garch_val_predictions.parquet"


def load_all_predictions(horizons: list[int] | None = None) -> pl.DataFrame:
    """Long-format predictions for every model in MODEL_REGISTRY that has
    a results file on disk. Missing files are skipped with a warning
    (e.g. a model not yet run) rather than raising.

    Returns:
        Columns: model, label, family, feature_set, horizon, date, y_true, y_pred.
    """
    horizons = horizons or HORIZONS
    frames = []

    for spec in MODEL_REGISTRY:
        if spec.combined_path is not None:
            if not spec.combined_path.exists():
                logger.warning(f"[results_loader] falta {spec.combined_path}, se omite {spec.model}")
                continue
            df = pl.read_parquet(spec.combined_path).filter(pl.col("horizon").is_in(horizons))
            df = df.select(["horizon", "date", "y_true", "y_pred"])
        else:
            per_horizon = []
            for h in horizons:
                path = Path(spec.path_template.format(h=h))
                if not path.exists():
                    logger.warning(f"[results_loader] falta {path}, se omite {spec.model} h={h}")
                    continue
                per_horizon.append(
                    pl.read_parquet(path).select(["date", "y_true", "y_pred"]).with_columns(
                        pl.lit(h).alias("horizon")
                    )
                )
            if not per_horizon:
                continue
            df = pl.concat(per_horizon)

        df = df.with_columns(
            pl.lit(spec.model).alias("model"),
            pl.lit(spec.label).alias("label"),
            pl.lit(spec.family).alias("family"),
            pl.lit(spec.feature_set).alias("feature_set"),
        )
        frames.append(df)

    if not frames:
        return pl.DataFrame(
            schema={
                "model": pl.Utf8, "label": pl.Utf8, "family": pl.Utf8,
                "feature_set": pl.Utf8, "horizon": pl.Int64, "date": pl.Date,
                "y_true": pl.Float64, "y_pred": pl.Float64,
            }
        )
    return pl.concat(frames, how="diagonal_relaxed").select(
        ["model", "label", "family", "feature_set", "horizon", "date", "y_true", "y_pred"]
    )


def load_garch_predictions(horizons: list[int] | None = None) -> pl.DataFrame:
    """GARCH tiene un esquema propio — predice varianza condicional, no
    retorno — así que no entra en el formato largo de load_all_predictions.

    Returns:
        Columns: horizon, date, variance_pred, sq_return_actual,
        predicted_vol, realized_vol (desvíos, raíz de las varianzas).
    """
    horizons = horizons or HORIZONS
    if not GARCH_PATH.exists():
        logger.warning(f"[results_loader] falta {GARCH_PATH}")
        return pl.DataFrame(
            schema={
                "horizon": pl.Int64, "date": pl.Date, "variance_pred": pl.Float64,
                "sq_return_actual": pl.Float64, "predicted_vol": pl.Float64, "realized_vol": pl.Float64,
            }
        )
    df = pl.read_parquet(GARCH_PATH).filter(pl.col("horizon").is_in(horizons))
    return df.with_columns(
        pl.col("variance_pred").sqrt().alias("predicted_vol"),
        pl.col("sq_return_actual").sqrt().alias("realized_vol"),
    )


def compute_naive_baseline(
    horizons: list[int] | None = None, dataset_name: str = "features_long"
) -> pl.DataFrame:
    """Naive (predecir retorno 0) RMSE/MAE por horizonte, calculado una
    sola vez desde features_long.parquet — fuente única de verdad para el
    baseline de comparación en todas las figuras, en vez de tomarlo de un
    modelo en particular (evita inconsistencias de milésimas por
    diferencias de warm-up entre modelos).
    """
    horizons = horizons or HORIZONS
    store = DuckDBStore()
    df = store.load_parquet(layer="features", name=dataset_name, version="v1")

    rows = []
    for h in horizons:
        y_val = df.filter(pl.col("split") == "val")[f"log_return_fwd_{h}"].drop_nulls().to_numpy()
        rmse, mae = naive_zero_metrics(y_val)
        rows.append({"horizon": h, "naive_rmse": rmse, "naive_mae": mae})
    return pl.DataFrame(rows)


def compute_metrics_summary(predictions: pl.DataFrame) -> pl.DataFrame:
    """RMSE/MAE por (model, label, family, feature_set, horizon), a partir
    del long-format de load_all_predictions.
    """
    return (
        predictions.group_by(["model", "label", "family", "feature_set", "horizon"])
        .agg(
            ((pl.col("y_true") - pl.col("y_pred")) ** 2).mean().sqrt().alias("rmse"),
            (pl.col("y_true") - pl.col("y_pred")).abs().mean().alias("mae"),
            pl.len().alias("n"),
        )
        .sort(["family", "model", "horizon"])
    )
