"""
features — Feature engineering.

Builds derived variables from processed data and saves them to the
``features`` data layer.  Only feature groups listed in
``settings.ACTIVE_FEATURES`` are computed during a pipeline run, allowing
fast iteration without rebuilding the full feature set each time.

Planned feature groups:
- technical    : moving averages, RSI, MACD, Bollinger Bands, ATR
- macro        : USD/ARS exchange rate, sovereign spread, inflation proxies
- calendar     : day-of-week, proximity to BYMA settlement dates
- sentiment    : (future) news / social media signals
"""
