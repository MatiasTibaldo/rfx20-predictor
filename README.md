# RFX20 Predictor

Modular ML pipeline for predicting the **RFX20** index — the main sovereign
bond benchmark of the Argentine market — across multiple short-term horizons
(1, 3, and 5 business days).

---

## Project structure

```
rfx20-predictor/
├── config/             # Pydantic BaseSettings — all configurable values
├── storage/            # DuckDB + Parquet persistence layer
├── ingestion/          # Raw data acquisition (APIs, files)
├── processing/         # Cleaning, alignment, train/val/test split
├── features/           # Feature engineering (technical, macro, calendar)
├── models/
│   ├── statistical/    # Naive, ARIMA, GARCH baselines
│   ├── ml/             # Ridge, RandomForest, XGBoost / LightGBM
│   └── deep_learning/  # MLP, LSTM, Transformer (requires [cpu] or [colab])
├── evaluation/         # Metrics, comparison, trading simulation
├── data/
│   ├── raw/            # Landing zone — unprocessed source files
│   ├── processed/      # Cleaned, normalised datasets
│   └── features/       # Engineered feature sets
├── results/            # Model outputs, reports, experiment DB
├── notebooks/          # Exploratory analysis and result visualisation
└── tests/              # Unit and integration tests
```

> `data/` and `results/` are excluded from version control.

---

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Base install (no deep learning)

```bash
uv sync
```

### With CPU-only PyTorch (local development, no GPU)

```bash
uv sync --extra cpu
```

### With standard PyTorch (Google Colab / GPU environment)

```bash
uv sync --extra colab
```

### Environment variables

```bash
cp .env.example .env
# Edit .env with your values
```

---

## Quick start

```python
from config import settings
from storage import DuckDBStore

store = DuckDBStore()

# Save a processed DataFrame
store.save_parquet(df, layer="processed", name="rfx20_ohlcv", version="v1")

# Load it back
df = store.load_parquet(layer="processed", name="rfx20_ohlcv", version="v1")

# Log an experiment run
store.log_run(
    model_name="RandomForest",
    params={"n_estimators": 200, "max_depth": 5},
    metrics={"rmse": 0.042, "directional_accuracy": 0.61},
)

# Compare all runs
runs = store.load_runs()
print(runs)
```

---

## Pipeline monitor (Streamlit)

```bash
uv run streamlit run app.py
```

## Running tests

```bash
uv run pytest
```

---

## Development environment

| Component | Version |
|-----------|---------|
| Python    | 3.11    |
| OS        | Ubuntu (Intel i7-12th gen, 32 GB RAM) |
| GPU       | None — CPU only |
| Package manager | uv |
