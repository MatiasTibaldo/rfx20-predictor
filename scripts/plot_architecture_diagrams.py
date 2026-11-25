"""
Diagramas esquemáticos (no basados en datos) para el Capítulo 3 (Estado del
Arte) y el Capítulo 4 (Metodología) de la tesis — apoyo visual para las
arquitecturas de Deep Learning y el pipeline de datos, descriptos hasta
ahora solo en ecuaciones/prosa. Misma paleta categórica que el resto de las
figuras del proyecto.

Genera:
  - fig8_lstm_gru.png           (Cap. 3.4.3/3.4.4 — compuertas de LSTM y GRU)
  - fig9_cnn_transformer.png    (Cap. 3.4.5/3.4.6 — CNN-LSTM y atención)
  - fig10_pipeline.png          (Cap. 4.1 — las 5 etapas del pipeline)

Uso: uv run python -m scripts.plot_architecture_diagrams
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

from config.settings import settings

FIGURES_DIR = settings.PROJECT_ROOT / "docs" / "figures"

COLOR_REAL = "#2a78d6"
COLOR_PRED = "#eb6834"
COLOR_AQUA = "#1baf7a"
COLOR_NAIVE = "#898781"
COLOR_TEXT = "#0b0b0b"
COLOR_GRID = "#e1e0d9"

plt.rcParams.update({"font.family": "sans-serif", "text.color": COLOR_TEXT, "font.size": 9.5})


def box(ax, xy, w, h, text, facecolor="white", edgecolor=COLOR_NAIVE, fontsize=9, fontcolor=None, lw=1.2):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.04",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=lw, zorder=2,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
            color=fontcolor or COLOR_TEXT, zorder=3, wrap=True)
    return patch


def op_circle(ax, xy, symbol, color=COLOR_NAIVE, r=0.055, fontsize=None):
    c = Circle(xy, r, facecolor="white", edgecolor=color, linewidth=1.3, zorder=4)
    ax.add_patch(c)
    fs = fontsize if fontsize is not None else max(7, min(11, 11 - (len(symbol) - 1) * 1.5))
    ax.text(xy[0], xy[1], symbol, ha="center", va="center", fontsize=fs, color=color, zorder=5)
    return c


def arrow(ax, start, end, color=COLOR_NAIVE, style="-|>", lw=1.1, connectionstyle="arc3,rad=0.0"):
    a = FancyArrowPatch(
        start, end, arrowstyle=style, color=color, linewidth=lw,
        mutation_scale=11, connectionstyle=connectionstyle, zorder=1,
    )
    ax.add_patch(a)
    return a


def _setup_ax(ax, xlim, ylim):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_lstm(ax) -> None:
    _setup_ax(ax, (0, 11), (-0.5, 6.5))
    ax.set_title("Celda LSTM", fontsize=11, loc="left", y=0.98)

    # Autopista del estado de celda C (arriba).
    arrow(ax, (0.3, 5.6), (10.3, 5.6), color=COLOR_REAL, lw=1.6)
    ax.text(0.1, 6.0, r"$C_{t-1}$", fontsize=10, color=COLOR_REAL)
    ax.text(9.95, 6.0, r"$C_t$", fontsize=10, color=COLOR_REAL)

    # Compuertas (sigma = decide cuanto pasa, tanh = candidato).
    box(ax, (1.7, 3.6), 1.7, 0.85, r"$f_t$: olvido" "\n" r"(σ)", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)
    box(ax, (3.9, 3.6), 1.7, 0.85, r"$i_t$: entrada" "\n" r"(σ)", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)
    box(ax, (6.1, 3.6), 1.9, 0.85, r"$\tilde{C}_t$: candidato" "\n(tanh)", facecolor=COLOR_AQUA, fontcolor="white", fontsize=8.5)
    box(ax, (7.3, 0.85), 1.7, 0.85, r"$o_t$: salida" "\n" r"(σ)", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)

    # Operaciones puntuales sobre la autopista de C.
    op_circle(ax, (2.55, 5.6), "×")
    op_circle(ax, (6.9, 5.6), "+")
    arrow(ax, (2.55, 4.5), (2.55, 5.52))
    arrow(ax, (4.75, 4.5), (6.65, 5.5))
    arrow(ax, (7.05, 4.5), (6.95, 5.5))

    # tanh(C_t) + compuerta de salida -> h_t
    op_circle(ax, (9.3, 2.9), "tanh", r=0.14, fontsize=8)
    arrow(ax, (9.3, 5.5), (9.3, 3.08), connectionstyle="arc3,rad=0.25", color=COLOR_REAL)
    op_circle(ax, (9.8, 0.45), "×")
    arrow(ax, (9.35, 2.75), (9.78, 0.53))
    arrow(ax, (8.3, 1.2), (9.72, 0.48))
    arrow(ax, (9.8, 0.35), (10.4, 0.0))
    ax.text(10.45, -0.15, r"$h_t$", fontsize=10, color=COLOR_PRED)

    # Entradas concatenadas [h_{t-1}, x_t].
    arrow(ax, (0.3, 0.3), (1.5, 0.3))
    ax.text(0.0, 0.3, r"$[h_{t-1},x_t]$", fontsize=8.5, ha="left", va="center")
    for target_x in (2.55, 4.75, 7.05, 8.45):
        arrow(ax, (1.6, 0.3), (target_x, 3.55), connectionstyle="arc3,rad=-0.15", lw=0.8, color=COLOR_GRID)


def draw_gru(ax) -> None:
    _setup_ax(ax, (0, 11), (0, 6.5))
    ax.set_title("Celda GRU", fontsize=11, loc="left", y=0.98)

    arrow(ax, (0.3, 4.6), (10.3, 4.6), color=COLOR_REAL, lw=1.6)
    ax.text(0.1, 5.0, r"$h_{t-1}$", fontsize=10, color=COLOR_REAL)
    ax.text(9.95, 5.0, r"$h_t$", fontsize=10, color=COLOR_REAL)

    box(ax, (2.6, 2.3), 1.8, 0.85, r"$z_t$: actualiz." "\n(σ)", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)
    box(ax, (4.7, 2.3), 1.8, 0.85, r"$r_t$: reinicio" "\n(σ)", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)
    box(ax, (6.8, 2.3), 2.0, 0.85, r"$\tilde{h}_t$: candidato" "\n(tanh)", facecolor=COLOR_AQUA, fontcolor="white", fontsize=8.5)

    op_circle(ax, (3.5, 4.6), "1-z", r=0.16, fontsize=9)
    op_circle(ax, (9.2, 4.6), "+")
    arrow(ax, (3.5, 3.15), (3.5, 4.5))
    arrow(ax, (7.8, 3.15), (9.05, 4.5))
    arrow(ax, (3.85, 4.5), (9.3, 4.5), connectionstyle="arc3,rad=0.3", color=COLOR_GRID, lw=0.9)

    arrow(ax, (0.3, 0.4), (2.4, 0.4))
    ax.text(0.0, 0.4, r"$[h_{t-1},x_t]$", fontsize=8.5, ha="left", va="center")
    for target_x in (3.5, 5.6, 7.8):
        arrow(ax, (2.5, 0.4), (target_x, 2.25), connectionstyle="arc3,rad=-0.15", lw=0.8, color=COLOR_GRID)


def draw_cnn_lstm(ax) -> None:
    _setup_ax(ax, (0, 11), (0, 4))
    ax.set_title("Arquitectura híbrida CNN-LSTM", fontsize=11, loc="left", y=0.95)
    steps = [
        ("Ventana\nde entrada\n(L pasos)", "white", COLOR_NAIVE, COLOR_TEXT),
        ("Conv1d\n(patrones\nlocales)", COLOR_AQUA, COLOR_AQUA, "white"),
        ("LSTM\n(dependencia\nsecuencial)", COLOR_PRED, COLOR_PRED, "white"),
        ("Capa\nlineal", COLOR_REAL, COLOR_REAL, "white"),
        ("Pronóstico\n" + r"$\hat{R}_{t+h}$", "white", COLOR_NAIVE, COLOR_TEXT),
    ]
    x = 0.3
    w, h, gap = 1.7, 1.6, 0.45
    for label, fc, ec, tc in steps:
        box(ax, (x, 1.2), w, h, label, facecolor=fc, edgecolor=ec, fontcolor=tc, fontsize=8.5)
        if x > 0.3:
            arrow(ax, (x - gap, 2.0), (x, 2.0))
        x += w + gap


def draw_transformer(ax) -> None:
    _setup_ax(ax, (0, 10), (0, 6))
    ax.set_title("Transformer encoder (atención)", fontsize=11, loc="left", y=0.98)

    box(ax, (3.5, 0.3), 3.0, 0.7, "Ventana de entrada (L pasos)", fontsize=8.5)
    arrow(ax, (5.0, 1.0), (5.0, 1.45))
    box(ax, (3.0, 1.5), 4.0, 0.7, "Proyección lineal + encoding posicional\n(seno/coseno)", fontsize=8)
    arrow(ax, (5.0, 2.2), (5.0, 2.65))
    box(ax, (2.3, 2.7), 5.4, 0.9, "Auto-atención multi-cabeza\n(cada paso atiende a todos los demás)",
        facecolor=COLOR_AQUA, fontcolor="white", fontsize=8.5)
    arrow(ax, (5.0, 3.6), (5.0, 4.05))
    box(ax, (3.5, 4.1), 3.0, 0.7, "Cabeza lineal de salida", facecolor=COLOR_PRED, fontcolor="white", fontsize=8.5)
    arrow(ax, (5.0, 4.8), (5.0, 5.25))
    ax.text(5.0, 5.5, "Pronóstico " + r"$\hat{R}_{t+h}$", ha="center", fontsize=9.5)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    draw_lstm(axes[0])
    draw_gru(axes[1])
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig8_lstm_gru.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1.3, 1]})
    draw_cnn_lstm(axes[0])
    draw_transformer(axes[1])
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig9_cnn_transformer.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 2.6))
    _setup_ax(ax, (0, 10.4), (0, 2.2))
    stages = ["Ingesta", "Procesamiento", "Ingeniería\nde features", "Particionamiento", "Modelado\ny evaluación"]
    colors = [COLOR_REAL, COLOR_REAL, COLOR_AQUA, COLOR_PRED, COLOR_PRED]
    x = 0.2
    w, h, gap = 1.7, 1.1, 0.35
    for i, (label, c) in enumerate(zip(stages, colors)):
        box(ax, (x, 0.6), w, h, f"{i+1}. {label}", facecolor=c, edgecolor=c, fontcolor="white", fontsize=9)
        if x > 0.2:
            arrow(ax, (x - gap, 1.15), (x, 1.15))
        x += w + gap
    ax.text(0.2, 2.0, "Pipeline de datos del proyecto", fontsize=11, ha="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig10_pipeline.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Guardadas en {FIGURES_DIR}")


if __name__ == "__main__":
    main()
