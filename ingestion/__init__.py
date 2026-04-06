"""
ingestion — Raw data acquisition.

Responsible for fetching market data from external sources (brokers, APIs,
flat files) and persisting it to the ``raw`` data layer via DuckDBStore.

Future modules in this package:
- yfinance_loader.py   : historical OHLCV via yfinance
- byma_loader.py       : real-time data from BYMA (Bolsas y Mercados Argentinos)
- csv_loader.py        : one-off ingestion from manually downloaded CSV files
"""
