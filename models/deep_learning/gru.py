"""
GRU architecture for Track B, Etapa 2 (Bloque 2 del plan de acción).

Same shape as models/deep_learning/lstm.py's LSTMRegressor — a single
recurrent layer + linear head — so the comparison against the Etapa 1
LSTM baseline isolates the recurrent cell type, not the surrounding
architecture. See docs/decisions/track_b_etapa2_gru_full_features.md.
"""

from __future__ import annotations

from torch import nn


class GRURegressor(nn.Module):
    """GRU followed by a linear head predicting a single scalar return."""

    def __init__(self, input_size: int, hidden_size: int = 32, num_layers: int = 1) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x):
        _, h_n = self.gru(x)
        last_hidden = h_n[-1]  # (batch, hidden_size) — final layer's hidden state
        return self.head(last_hidden)
