"""Entry point for Nodo 3 (Processing). Invoked by the Streamlit pipeline as a subprocess."""
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
    state.setdefault("nodes", {})["processing"] = {"status": "running"}
    save_state(state)

    try:
        from processing.pipeline import ProcessingPipeline
        result = ProcessingPipeline().run()
        state = load_state()
        state["nodes"]["processing"] = {
            "status": "completed",
            "stats": {
                "tickers_processed": len(result.tickers_processed),
                "tickers_failed": len(result.tickers_failed),
                "long_rows": result.long_rows,
                "wide_rows": result.wide_rows,
                "reconstruction_flagged": result.reconstruction_flagged,
            },
        }
        save_state(state)
        print("Nodo 3 completado.")
    except Exception as exc:
        state = load_state()
        state["nodes"]["processing"] = {"status": "error", "error": str(exc)}
        save_state(state)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
