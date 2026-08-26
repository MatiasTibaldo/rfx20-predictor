"""Entry point for Nodo 4 (Features). Invoked by the Streamlit pipeline as a subprocess."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "results" / "pipeline_state.json"

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"nodes": {}}

def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str))

def main() -> None:
    state = load_state()
    state.setdefault("nodes", {})["features"] = {"status": "running"}
    save_state(state)

    try:
        from features.pipeline import FeaturesPipeline
        result = FeaturesPipeline().run()
        state = load_state()
        state["nodes"]["features"] = {
            "status": "completed",
            "stats": {
                "tickers_processed": len(result.tickers_processed),
                "tickers_failed": len(result.tickers_failed),
                "components_rows": result.components_rows,
                "components_columns": result.components_columns,
                "index_rows": result.index_rows,
                "index_columns": result.index_columns,
                "macro_rows": result.macro_rows,
                "macro_columns": result.macro_columns,
                "features_long_rows": result.features_long_rows,
                "features_long_columns": result.features_long_columns,
            },
        }
        save_state(state)
        print("Nodo 4 (Etapas 1-4) completado.")
    except Exception as exc:
        state = load_state()
        state["nodes"]["features"] = {"status": "error", "error": str(exc)}
        save_state(state)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
