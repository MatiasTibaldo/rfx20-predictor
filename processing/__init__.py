"""
processing — Data cleaning and transformation.

Transforms raw ingested data into analysis-ready datasets stored in the
``processed`` data layer.

Typical responsibilities:
- Backward split adjustment of OHLCV series.
- Patching known dirty data values.
- Index membership tagging.
- Return computation (log and simple, spot and forward).
- Dummy variables for macro events.
- Wide and long format dataset persistence.
- Index reconstruction and spot validation.
"""

# Import order matters: lower-level modules first so that pipeline.py
# can safely use relative imports without hitting partial-init cycles.
from .adjustments import SplitAdjuster
from .splits import SplitEvent, adjust_ticker, load_splits, run
from .cleaner import (
    apply_composition_price_corrections,
    apply_corrections,
    apply_corrections_all,
    load_composition_price_corrections,
    load_dirty_data,
)
from .filter import add_index_membership, add_index_membership_all
from .returns import add_returns, add_returns_all
from .dummies import add_dummies, add_dummies_all
from .wide_long import build_long, build_wide, save_datasets
from .reconstruction import load_divisores, reconstruct_index, validate_reconstruction
from .reconstruction import run as run_reconstruction
from .pipeline import ProcessingPipeline, ProcessingResult

__all__ = [
    # adjustments
    "SplitAdjuster",
    # splits (legacy interface)
    "SplitEvent",
    "adjust_ticker",
    "load_splits",
    "run",
    # cleaner
    "apply_corrections",
    "apply_corrections_all",
    "apply_composition_price_corrections",
    "load_dirty_data",
    "load_composition_price_corrections",
    # filter
    "add_index_membership",
    "add_index_membership_all",
    # returns
    "add_returns",
    "add_returns_all",
    # dummies
    "add_dummies",
    "add_dummies_all",
    # wide_long
    "build_long",
    "build_wide",
    "save_datasets",
    # reconstruction
    "load_divisores",
    "reconstruct_index",
    "validate_reconstruction",
    "run_reconstruction",
    # pipeline
    "ProcessingPipeline",
    "ProcessingResult",
]
