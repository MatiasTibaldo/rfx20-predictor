"""
evaluation — Model evaluation and comparison.

Computes performance metrics on the hold-out test set and persists results
via DuckDBStore so that runs across different models and horizons can be
compared in a reproducible way.

Metrics of interest:
- Regression : RMSE, MAE, MAPE, directional accuracy
- Trading    : Sharpe ratio (simulated), max drawdown of a naive strategy
               that follows model signals

Results are also saved as Parquet snapshots in ``results/`` for downstream
visualisation in notebooks.
"""
