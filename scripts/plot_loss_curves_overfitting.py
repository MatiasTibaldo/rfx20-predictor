"""
Figura de curvas de pérdida train vs. early-stopping para la tesis (sección
5.3.2, seguimiento del feedback de los directores: "incorporar curvas
representativas... sin recargar el cuerpo del trabajo"). Dos paneles desde
`results/punto6_dl_diagnostics_full_sweep/full_sweep.json` (36 combinaciones
ya corridas, Punto 6):

- Panel izquierdo: LSTM-compA h=5, la combinación con mayor `gap_last` de
  las 36 (0,1191) — el caso más degradado.
- Panel derecho: CNN-LSTM-baseline h=1, la de menor `gap_last` (0,0003) — el
  contraste más sano.

Uso: uv run python scripts/plot_loss_curves_overfitting.py
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt

from config.settings import settings

COLOR_TRAIN = "#2a78d6"  # mismo azul "Real" de evaluation/figures.py
COLOR_ES = "#eb6834"  # mismo naranja "Predicho" de evaluation/figures.py
COLOR_GRID = "#e1e0d9"

SWEEP_PATH = settings.RESULTS_DIR / "punto6_dl_diagnostics_full_sweep" / "full_sweep.json"
OUT_PATH = settings.PROJECT_ROOT / "docs" / "figures" / "loss_curves_overfitting.png"


def find_combo(rows: list[dict], dataset: str, model: str, horizon: int) -> dict:
    for row in rows:
        if row["dataset"] == dataset and row["model"] == model and row["horizon"] == horizon:
            return row
    raise ValueError(f"No se encontró {dataset}/{model}/h={horizon}")


def plot_panel(ax, row: dict, title: str) -> None:
    epochs = list(range(1, len(row["history"]) + 1))
    ax.plot(epochs, row["train_history"], color=COLOR_TRAIN, linewidth=1.4, label="Pérdida de train")
    ax.plot(epochs, row["history"], color=COLOR_ES, linewidth=1.4, label="Pérdida de early stopping")
    ax.axvline(row["best_epoch"] + 1, color=COLOR_GRID, linestyle="--", linewidth=1.0, zorder=0)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Época")
    ax.set_ylabel("Pérdida (MSE)")
    ax.grid(color=COLOR_GRID, linewidth=0.6)


def main() -> None:
    rows = json.loads(SWEEP_PATH.read_text())
    degraded = find_combo(rows, "compA", "LSTM", 5)
    healthy = find_combo(rows, "baseline", "CNN-LSTM", 1)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    plot_panel(
        axes[0],
        degraded,
        f"LSTM, compA, h=5 (más degradado, gap={degraded['gap_last']:.3f})",
    )
    plot_panel(
        axes[1],
        healthy,
        f"CNN-LSTM, baseline, h=1 (más sano, gap={healthy['gap_last']:.3f})",
    )
    axes[0].legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardado en {OUT_PATH}")


if __name__ == "__main__":
    main()
