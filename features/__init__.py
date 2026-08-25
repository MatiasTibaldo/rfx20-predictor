"""
features — Feature engineering.

Builds derived variables from processed data and saves them to the
``features`` data layer. Nodo 4 is being built incrementally in etapas
(see docs/plan_de_accion.md) rather than all at once.

Feature groups:
- technical    : moving averages, RSI, MACD, Bollinger Bands — DONE (Etapa 1),
                 see technical.py. Computed for the 27 index components
                 (ohlcv_long) and for the RFX20 index itself (rfx20_spot).
- volatility   : realized volatility (rolling std of log_return) — DONE
                 (Etapa 1), see volatility.py. Same two levels as technical.
- target       : RFX20 index log-return target at t+1/3/5 — DONE (Etapa 1),
                 see target.py.
- macro        : USD/ARS exchange rate spreads, term spread, IPC (with
                 publication lag), futures implied rate / term spread —
                 PENDING, next etapa.
- fractional differentiation : exploratory, non-blocking — PENDING.
- calendar     : day-of-week, proximity to BYMA settlement dates — PENDING.
- split        : temporal train/val/test partition (70/15/15) — PENDING,
                 last etapa of Nodo 4 once all feature groups are joined.
- sentiment    : (future) news / social media signals.
"""
