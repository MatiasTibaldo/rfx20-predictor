"""
Híbrido CNN-LSTM para Track B, Etapa 3 (Bloque 2 del plan de acción).

Una capa Conv1D actúa como extractor de patrones locales sobre el eje
temporal de la ventana (equivalente a un "template matching" de formas
cortas en la serie) antes de pasar la representación resultante a una
LSTM, que captura dependencia secuencial de más largo alcance. Mismo
protocolo de entrenamiento/evaluación que LSTM/GRU — ver
docs/decisions/track_b_etapa3_tft_hibrido.md.
"""

from __future__ import annotations

from torch import nn


class CNNLSTMRegressor(nn.Module):
    """Conv1D -> LSTM -> cabeza lineal a un escalar."""

    def __init__(
        self,
        input_size: int,
        conv_channels: int = 16,
        kernel_size: int = 3,
        hidden_size: int = 32,
        num_layers: int = 1,
    ) -> None:
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels=input_size,
            out_channels=conv_channels,
            kernel_size=kernel_size,
            padding=kernel_size // 2,
        )
        self.activation = nn.ReLU()
        self.lstm = nn.LSTM(
            input_size=conv_channels,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.head = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x: (batch, lookback, n_features) -> Conv1d espera (batch, canales, longitud)
        x = x.transpose(1, 2)
        x = self.activation(self.conv(x))
        x = x.transpose(1, 2)  # de vuelta a (batch, lookback, conv_channels) para la LSTM
        _, (h_n, _) = self.lstm(x)
        last_hidden = h_n[-1]
        return self.head(last_hidden)
