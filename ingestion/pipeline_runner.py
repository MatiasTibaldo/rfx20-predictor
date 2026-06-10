"""
Runner for Node 2: OHLCV ingestion for all RFX20 tickers.

Fetches OHLCV data from Primary S.A. for 2018-01-01 through today and
saves each ticker as a Parquet file in data/raw/v1/. Updates
results/pipeline_state.json on completion.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

from loguru import logger

from config.settings import settings
from ingestion.pipeline import IngestionPipeline

_STATE_PATH = settings.RESULTS_DIR / "pipeline_state.json"


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
    state["nodes"]["ohlcv"]["status"] = "running"
    _save_state(state)

    try:
        pipeline = IngestionPipeline()
        results = pipeline.run_rfx20(
            date_from=date(2018, 1, 1),
            date_to=date.today(),
            version="v1",
        )

        successful = [t for t, ok in results.items() if ok]
        failed = [t for t, ok in results.items() if not ok]

        state["nodes"]["ohlcv"] = {
            "status": "completed",
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "stats": {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "failed_tickers": failed,
            },
        }
        _save_state(state)
        logger.info(
            f"[pipeline_runner] Completed: {len(successful)} ok, {len(failed)} failed."
        )

    except Exception as exc:
        state["nodes"]["ohlcv"] = {
            "status": "error",
            "error": str(exc),
            "failed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        _save_state(state)
        logger.error(f"[pipeline_runner] Failed: {exc}")
        raise


if __name__ == "__main__":
    run()
