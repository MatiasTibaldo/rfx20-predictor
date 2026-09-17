"""
Test de reproducibilidad para Track B (Bloque 2 — LSTM y GRU).

CLAUDE.md exige reproducibilidad para el código de modelos (excepción a la
regla general de "sin tests en esta etapa" para ingestion/processing). Este
test no valida capacidad predictiva (eso lo documentan
docs/decisions/lstm_baseline_track_b.md y
docs/decisions/track_b_etapa2_gru_full_features.md con datos reales) — solo
que dos corridas con la misma seed producen exactamente el mismo resultado,
dado que el entrenamiento de una red introduce fuentes de no-determinismo
(inicialización de pesos, orden de shuffle del DataLoader) que los modelos
de Track A no tenían. Parametrizado sobre las cuatro arquitecturas de
Track B (LSTM, GRU, CNN-LSTM, TFT-lite) porque cada una hereda la misma
obligación de reproducibilidad.

Ejecutar:
    uv run pytest tests/test_deep_learning.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from models.deep_learning.cnn_lstm import CNNLSTMRegressor
from models.deep_learning.common import train_with_early_stopping
from models.deep_learning.gru import GRURegressor
from models.deep_learning.lstm import LSTMRegressor
from models.deep_learning.tft_lite import TFTLiteRegressor

N_FEATURES = 4


def _synthetic_sequences():
    """Small deterministic synthetic dataset — no dependency on real data files."""
    rng = np.random.default_rng(0)
    X_fit = rng.normal(size=(48, 6, N_FEATURES)).astype(np.float32)
    y_fit = rng.normal(size=48).astype(np.float32)
    X_earlystop = rng.normal(size=(12, 6, N_FEATURES)).astype(np.float32)
    y_earlystop = rng.normal(size=12).astype(np.float32)
    return X_fit, y_fit, X_earlystop, y_earlystop


@pytest.mark.parametrize(
    "regressor_cls", [LSTMRegressor, GRURegressor, CNNLSTMRegressor, TFTLiteRegressor]
)
def test_train_with_early_stopping_is_reproducible(regressor_cls):
    X_fit, y_fit, X_earlystop, y_earlystop = _synthetic_sequences()

    def model_factory():
        # Cada arquitectura usa sus propios defaults (hidden_size, d_model,
        # etc. difieren en nombre) — no forzamos un tamaño uniforme, solo
        # que sea reproducible.
        return regressor_cls(input_size=N_FEATURES)

    _, best_epoch_a, loss_a, history_a = train_with_early_stopping(
        model_factory, X_fit, y_fit, X_earlystop, y_earlystop, max_epochs=10, patience=10
    )
    _, best_epoch_b, loss_b, history_b = train_with_early_stopping(
        model_factory, X_fit, y_fit, X_earlystop, y_earlystop, max_epochs=10, patience=10
    )

    assert best_epoch_a == best_epoch_b
    assert loss_a == loss_b
    assert history_a == history_b
