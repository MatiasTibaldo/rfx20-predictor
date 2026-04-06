"""
storage — Data persistence layer.

Provides a unified interface for reading/writing versioned Parquet files
across the three data layers (raw, processed, features) and for logging
experiment runs to a DuckDB database.

Usage:
    from storage import DuckDBStore
    store = DuckDBStore()
"""

from .store import DuckDBStore

__all__ = ["DuckDBStore"]
