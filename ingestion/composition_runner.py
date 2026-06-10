"""
Runner for Node 1: RFX20 composition ingestion.

Loads RFX20 composition + spot + dividends CSVs and saves them to Parquet
under data/raw/v1/. Updates results/pipeline_state.json on completion.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from config.settings import settings
from ingestion.composition import RFX20CompositionLoader
from storage.store import DuckDBStore

_STATE_PATH = settings.RESULTS_DIR / "pipeline_state.json"
_COMPOSITION_BASE = settings.RAW_DIR / "rfx20_composition"


def _load_state() -> dict:
    if _STATE_PATH.exists():
        return json.loads(_STATE_PATH.read_text())
    return {
        "nodes": {
            "composition": {"status": "pending"},
            "ohlcv": {"status": "pending"},
            "processing": {"status": "pending"},
            "features": {"status": "pending"},
            "models": {"status": "pending"},
        }
    }


def _save_state(state: dict) -> None:
    _STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def run() -> None:
    state = _load_state()
    state["nodes"]["composition"]["status"] = "running"
    _save_state(state)

    try:
        loader = RFX20CompositionLoader()
        store = DuckDBStore()
        loader.save_to_raw(_COMPOSITION_BASE, store)

        comp_df = store.load_parquet(layer="raw", name="rfx20_composition", version="v1")
        spot_df = store.load_parquet(layer="raw", name="rfx20_spot", version="v1")

        state["nodes"]["composition"] = {
            "status": "completed",
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "stats": {
                "composition_rows": len(comp_df),
                "composition_tickers": comp_df["ticker"].n_unique(),
                "composition_date_min": str(comp_df["date"].min()),
                "composition_date_max": str(comp_df["date"].max()),
                "spot_rows": len(spot_df),
                "spot_date_min": str(spot_df["date"].min()),
                "spot_date_max": str(spot_df["date"].max()),
            },
        }
        _save_state(state)
        logger.info("[composition_runner] Completed successfully.")

    except Exception as exc:
        state["nodes"]["composition"] = {
            "status": "error",
            "error": str(exc),
            "failed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        _save_state(state)
        logger.error(f"[composition_runner] Failed: {exc}")
        raise


if __name__ == "__main__":
    run()
