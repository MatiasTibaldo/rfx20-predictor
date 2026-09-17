"""
"TFT-lite" para Track B, Etapa 3 (Bloque 2 del plan de acción) — evaluación
PRELIMINAR de una arquitectura basada en atención, no una implementación
completa de Temporal Fusion Transformer (Lim et al., 2019).

Decisión de alcance (ver docs/decisions/track_b_etapa3_tft_hibrido.md): el
TFT real incluye variable selection networks, gated residual networks,
un encoder de covariables estáticas y salidas por cuantiles — pensado para
datasets con múltiples series/entidades y covariables estáticas, ninguna
de las cuales aplica acá (una sola serie, sin covariables estáticas, ~1600
filas de train). El propio plan de acción ya encuadra este punto como
"evaluación preliminar de TFT", no como entregable duro. Esta clase toma
el ingrediente de TFT más relevante para esta pregunta puntual — atención
multi-cabeza sobre la ventana de lookback, en vez de una celda
recurrente — y nada más.
"""

from __future__ import annotations

import math

import torch
from torch import nn


def _sinusoidal_positional_encoding(seq_len: int, d_model: int, device: torch.device) -> torch.Tensor:
    position = torch.arange(seq_len, device=device).unsqueeze(1)
    div_term = torch.exp(
        torch.arange(0, d_model, 2, device=device) * (-math.log(10000.0) / d_model)
    )
    pe = torch.zeros(seq_len, d_model, device=device)
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    return pe.unsqueeze(0)  # (1, seq_len, d_model)


class TFTLiteRegressor(nn.Module):
    """Proyección lineal + encoding posicional + TransformerEncoder -> cabeza lineal."""

    def __init__(
        self,
        input_size: int,
        d_model: int = 32,
        nhead: int = 4,
        num_layers: int = 1,
        dim_feedforward: int = 64,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x):
        # x: (batch, lookback, n_features)
        h = self.input_proj(x)
        pe = _sinusoidal_positional_encoding(h.size(1), h.size(2), h.device)
        h = h + pe
        h = self.encoder(h)
        last_step = h[:, -1, :]  # representación del último paso, análogo al hidden final de la LSTM
        return self.head(last_step)
