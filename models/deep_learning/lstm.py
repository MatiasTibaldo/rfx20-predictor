"""
LSTM architecture for Track B, Etapa 1 (Bloque 2 del plan de acción).

Deliberately simple — single-direction, no attention — to serve as a
baseline before GRU and the preliminary TFT/hybrid CNN-LSTM evaluation in
later etapas. See docs/decisions/lstm_baseline_track_b.md.
"""

from __future__ import annotations

from torch import nn


class LSTMRegressor(nn.Module):
    """LSTM followed by a linear head predicting a single scalar return."""

    def __init__(self, input_size: int, hidden_size: int = 32, num_layers: int = 1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x):
        _, (h_n, _) = self.lstm(x)
        last_hidden = h_n[-1]  # (batch, hidden_size) — final layer's hidden state
        return self.head(last_hidden)
