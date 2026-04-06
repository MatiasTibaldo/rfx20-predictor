"""
models.deep_learning — PyTorch neural network models.

Requires the [cpu] optional dependency group for local development:
    uv sync --extra cpu

Or the [colab] group when running on Google Colab with GPU:
    uv sync --extra colab   (or: pip install rfx20-predictor[colab])

Planned implementations:
- MLPModel        : Multi-layer perceptron for tabular feature input.
- LSTMModel       : Sequence model for raw price series.
- TransformerModel: Attention-based model for multi-variate time series.

Imports from this sub-package will raise ImportError with a helpful message
if torch is not installed, so the rest of the pipeline remains functional
even without the deep-learning dependencies.
"""
