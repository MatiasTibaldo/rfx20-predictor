"""
processing — Data cleaning and transformation.

Transforms raw ingested data into analysis-ready datasets stored in the
``processed`` data layer.

Typical responsibilities:
- Handling missing values and outliers in OHLCV series.
- Aligning time indices to the Argentine business calendar.
- Currency / inflation adjustments (ARS nominal → real if needed).
- Splitting into train / validation / test sets respecting temporal order.
"""
