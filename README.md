# RFX20 Predictor

Modular ML pipeline for predicting the **RFX20** index — the main sovereign
bond benchmark of the Argentine market — across multiple short-term horizons
(1, 3, and 5 business days).

Master's thesis project — Universidad Austral. Internal tool at Primary S.A.

---

## Status — June 2026

| Module | Status |
|--------|--------|
| Nodo 1: Historical composition (27 tickers, 2018→present) | Done |
| Nodo 2: OHLCV series ingestion from Primary S.A. API | Done |
| Split adjustment module (`processing/adjustments.py`) | Done |
| Streamlit pipeline monitor (`app.py`) | Done |
| Nodo 3: Processing (returns, alignment, dummies) | In progress |
| Nodo 4: Feature engineering | Pending |
| Nodo 5+: Models, evaluation, pipeline | Pending |

---

## Project structure

```
rfx20-predictor/
├── config/             # Pydantic settings + splits.yaml (confirmed splits & macro events)
├── storage/            # DuckDB + Parquet persistence layer
├── ingestion/          # Raw data acquisition from Primary S.A. API
├── processing/         # OHLCV cleaning, split adjustments (Nodo 3 in progress)
├── features/           # Feature engineering (pending)
├── models/
│   ├── statistical/    # ARIMA, GARCH baselines
│   ├── ml/             # XGBoost, LightGBM, RF
│   └── deep_learning/  # LSTM, Transformer (requires [cpu] or [colab])
├── evaluation/         # Metrics, backtesting (pending)
├── scripts/            # Utility scripts (validate_variation.py)
├── docs/
│   └── decisions/      # Methodological decision records for the thesis
├── data/
│   ├── raw/            # Immutable source files — do not modify
│   ├── processed/      # Cleaned, adjusted datasets (output of Nodo 3)
│   └── features/       # Engineered feature sets (output of Nodo 4)
├── results/            # Experiment DuckDB + pipeline_state.json
├── notebooks/          # Exploratory analysis
├── tests/              # Test suite
├── app.py              # Streamlit pipeline monitor
└── main.py             # Pipeline entry point
```

> `data/` and `results/` are excluded from version control.

---

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

### Base install

```bash
uv sync
```

### With CPU-only PyTorch (local, no GPU)

```bash
uv sync --extra cpu
```

### With standard PyTorch (Google Colab / GPU)

```bash
uv sync --extra colab
```

### API credentials

Create a `.env` file at the project root with your Primary S.A. credentials:

```bash
PRIMARY_API_KEY=your_key_here
PRIMARY_API_SECRET=your_secret_here
```

---

## Running the pipeline monitor

```bash
uv run streamlit run app.py
```

Provides live visibility into ingestion state, OHLCV coverage, and data
validation results across all 27 index components.

---

## Data validation

```bash
uv run python scripts/validate_variation.py --threshold 30
```

Detects day-over-day price jumps (close→open) above the threshold.
Results are cross-referenced against `config/splits.yaml` to classify
each alert as a confirmed split, a macro event, or dirty data.

---

## Key configuration

- **`config/splits.yaml`**: confirmed split events and macro dummies (PASO 2019,
  elections 2023). Add new entries here when new splits are detected — no code changes needed.
- **`docs/decisions/`**: methodological decision records, primary source for the
  thesis methodology section.

---

## Development environment

| Component | Version |
|-----------|---------|
| Python | 3.11 |
| OS | Ubuntu (Intel i7-12th gen, 32 GB RAM) |
| GPU | None — CPU only |
| Package manager | uv |
| Linter | ruff |
