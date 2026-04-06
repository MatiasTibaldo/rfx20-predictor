"""
models — Forecasting model implementations.

Sub-packages:
- statistical    : Baseline and classical time-series models
                   (Naive, ARIMA, SARIMA, GARCH).
- ml             : Scikit-learn compatible models
                   (LinearRegression, Ridge, RandomForest, XGBoost, LightGBM).
- deep_learning  : Neural network architectures
                   (MLP, LSTM, Transformer) — requires the [cpu] or [colab]
                   optional dependency group.

All models expose a common interface:
    fit(X_train, y_train) -> self
    predict(X) -> np.ndarray
so they can be swapped transparently in the evaluation pipeline.
"""
