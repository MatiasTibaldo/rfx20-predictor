"""
evaluation — Model evaluation, comparison, and visualization.

``results_loader.py`` unifies every Bloque 2 (Track A + Track B) model's
val predictions into one long-format schema, regardless of how each
family happened to persist them. ``figures.py`` renders that into
thesis-ready static PNGs (``docs/figures/``); the same loader backs the
"Modelos" section of the Streamlit dashboard (``app.py``) for interactive
exploration. See docs/decisions/track_a_b_sintesis_direccion_volatilidad.md
for what these results mean.

Bloque 3 (comparación multicriterio: RMSE/MAE/MAPE, hit ratio,
backtesting con Sharpe/drawdown, ensamble) todavía no arrancó — este
paquete crecerá con esa lógica cuando lo haga.
"""
