"""
models.ml — Scikit-learn compatible machine learning models.

Planned implementations:
- LinearModel     : Ridge / Lasso regression with optional polynomial features.
- TreeModel       : RandomForestRegressor and GradientBoostingRegressor.
- BoostingModel   : XGBoost / LightGBM wrappers with early stopping.

All wrappers follow the sklearn estimator protocol so they work inside
``Pipeline`` and ``GridSearchCV`` without modification.
"""
