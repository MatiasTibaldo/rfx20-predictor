"""
Tests para evaluation/results_loader.py — CLAUDE.md exige tests para el
código de evaluación (excepción a la regla general de "sin tests en esta
etapa"). Cubre la lógica de cómputo (RMSE/MAE agrupado), no la lectura de
archivos reales — eso ya se verifica end-to-end corriendo
`uv run python -m evaluation.figures` sobre los resultados reales.

Ejecutar:
    uv run pytest tests/test_evaluation.py -v
"""

from __future__ import annotations

import math

import polars as pl

from evaluation.results_loader import compute_metrics_summary, load_all_predictions


def test_compute_metrics_summary_matches_hand_computed_rmse_mae():
    predictions = pl.DataFrame(
        {
            "model": ["a", "a", "a", "b", "b", "b"],
            "label": ["A", "A", "A", "B", "B", "B"],
            "family": ["fam1", "fam1", "fam1", "fam2", "fam2", "fam2"],
            "feature_set": ["narrow"] * 6,
            "horizon": [1, 1, 1, 1, 1, 1],
            "date": [1, 2, 3, 1, 2, 3],
            "y_true": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
            "y_pred": [1.0, 2.0, 3.0, 0.0, 0.0, 0.0],
        }
    )

    summary = compute_metrics_summary(predictions).sort("model")

    model_a = summary.filter(pl.col("model") == "a").row(0, named=True)
    assert model_a["rmse"] == 0.0
    assert model_a["mae"] == 0.0
    assert model_a["n"] == 3

    model_b = summary.filter(pl.col("model") == "b").row(0, named=True)
    expected_rmse = math.sqrt((1.0**2 + 2.0**2 + 3.0**2) / 3)
    expected_mae = (1.0 + 2.0 + 3.0) / 3
    assert math.isclose(model_b["rmse"], expected_rmse)
    assert math.isclose(model_b["mae"], expected_mae)


def test_load_all_predictions_skips_missing_files_without_raising():
    # No hay resultados persistidos para un horizonte inexistente — debe
    # devolver un DataFrame vacío con el esquema esperado, no lanzar.
    result = load_all_predictions(horizons=[999])
    assert result.is_empty()
    assert result.columns == [
        "model", "label", "family", "feature_set", "horizon", "date", "y_true", "y_pred",
    ]
