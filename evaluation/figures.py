"""
Figuras estáticas (PNG, matplotlib) de Bloque 2 (Track A + Track B) para
inserción directa en la tesis — ver docs/decisions/track_a_b_sintesis_direccion_volatilidad.md
para la lectura completa de estos resultados.

Tres figuras, cobertura completa de todos los modelos y horizontes ya
corridos:
  1. rmse_comparison.png — RMSE de cada modelo vs. el naive, por horizonte.
  2. predicted_vs_real_h{1,3,5}.png — grilla con el predicho vs. el real
     de cada modelo de retorno (todos salvo GARCH, que predice varianza).
  3. garch_volatility.png — volatilidad predicha (GARCH) vs. realizada.

Paleta: siguiendo la convención "el color sigue a la entidad" — las
familias de modelos (Track A Estadístico / Track A ML clásico / Track B
Deep Learning) usan los slots categóricos 1/2/3 del set validado (azul/
naranja/aqua, mismo orden en toda la figura), y las grillas predicho-vs-real
usan siempre azul=Real, naranja=Predicho, sin importar el modelo — así la
identidad de cada serie es reconocible de una figura a otra.

Uso: uv run python -m evaluation.figures
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import polars as pl
from loguru import logger

from config.settings import settings
from evaluation.results_loader import (
    TRACK_A_ESTADISTICO,
    TRACK_A_ML,
    TRACK_B_DL,
    compute_metrics_summary,
    compute_naive_baseline,
    load_all_predictions,
    load_garch_predictions,
)
from models.ml.common import HORIZONS

FIGURES_DIR = settings.PROJECT_ROOT / "docs" / "figures"

# Paleta categórica validada (referencias/palette.md), modo claro — slots 1-3.
COLOR_REAL = "#2a78d6"  # slot 1, azul — "Real" en todas las grillas
COLOR_PRED = "#eb6834"  # slot 2, naranja — "Predicho" en todas las grillas
COLOR_FAMILY = {
    TRACK_A_ESTADISTICO: "#2a78d6",  # slot 1, azul
    TRACK_A_ML: "#eb6834",  # slot 2, naranja
    TRACK_B_DL: "#1baf7a",  # slot 3, aqua
}
COLOR_NAIVE = "#898781"  # ink "muted" — referencia neutral, no es una serie
COLOR_TEXT = "#0b0b0b"
COLOR_MUTED = "#898781"
COLOR_GRID = "#e1e0d9"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "axes.edgecolor": COLOR_MUTED,
        "axes.labelcolor": COLOR_TEXT,
        "text.color": COLOR_TEXT,
        "xtick.color": COLOR_MUTED,
        "ytick.color": COLOR_MUTED,
        "axes.grid": True,
        "grid.color": COLOR_GRID,
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def fig_rmse_comparison(horizons: list[int] | None = None) -> None:
    """Un panel por horizonte: RMSE de cada modelo (barras horizontales,
    coloreadas por familia, ordenadas ascendente) vs. la línea de
    referencia del naive.
    """
    horizons = horizons or HORIZONS
    preds = load_all_predictions(horizons)
    summary = compute_metrics_summary(preds)
    naive = compute_naive_baseline(horizons)

    fig, axes = plt.subplots(1, len(horizons), figsize=(15, 6), sharex=False)
    if len(horizons) == 1:
        axes = [axes]

    for ax, h in zip(axes, horizons):
        rows = summary.filter(pl.col("horizon") == h).sort("rmse", descending=True)
        naive_rmse = naive.filter(pl.col("horizon") == h)["naive_rmse"].item()

        labels = rows["label"].to_list()
        values = rows["rmse"].to_list()
        colors = [COLOR_FAMILY[fam] for fam in rows["family"].to_list()]

        y_pos = range(len(labels))
        ax.barh(y_pos, values, color=colors, height=0.65)
        ax.axvline(naive_rmse, color=COLOR_NAIVE, linestyle="-", linewidth=1.5, zorder=3)
        ax.text(
            naive_rmse, len(labels) - 0.3, " naive", color=COLOR_NAIVE, fontsize=8, va="bottom"
        )

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("RMSE (val)")
        ax.set_title(f"Horizonte {h} día{'s' if h > 1 else ''}", fontsize=11, loc="left")
        ax.grid(axis="y", visible=False)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color) for color in COLOR_FAMILY.values()
    ]
    fig.legend(
        legend_handles,
        list(COLOR_FAMILY.keys()),
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.suptitle(
        "Comparación de RMSE por modelo y horizonte — línea gris = naive (predecir retorno 0)",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))

    out_path = FIGURES_DIR / "rmse_comparison.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[figures] guardado {out_path}")


def fig_predicted_vs_real_grid(horizon: int) -> None:
    """Grilla con un panel por modelo de retorno (todos salvo GARCH) —
    línea real vs. predicho sobre el período de validación.
    """
    preds = load_all_predictions([horizon]).sort(["model", "date"])
    models = preds.select(["model", "label"]).unique().sort("model").rows()

    n = len(models)
    n_cols = 4
    n_rows = math.ceil(n / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4.2 * n_cols, 3 * n_rows), sharey=True)
    axes_flat = axes.flatten() if n > 1 else [axes]

    for ax, (model, label) in zip(axes_flat, models):
        sub = preds.filter(pl.col("model") == model)
        dates = sub["date"].to_list()
        ax.plot(dates, sub["y_true"].to_list(), color=COLOR_REAL, linewidth=1.0, label="Real")
        ax.plot(dates, sub["y_pred"].to_list(), color=COLOR_PRED, linewidth=1.0, label="Predicho")
        ax.axhline(0, color=COLOR_GRID, linewidth=0.8, zorder=0)
        ax.set_title(label, fontsize=10, loc="left")
        ax.tick_params(axis="x", labelrotation=30, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)

    for ax in axes_flat[n:]:
        ax.axis("off")

    handles, labels_ = axes_flat[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(
        f"Predicho vs. real — log_return_fwd_{horizon} (val, todos los modelos)", fontsize=12
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))

    out_path = FIGURES_DIR / f"predicted_vs_real_h{horizon}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[figures] guardado {out_path}")


def fig_garch_volatility(horizons: list[int] | None = None) -> None:
    """Un panel por horizonte: volatilidad predicha (GARCH) vs. realizada."""
    horizons = horizons or HORIZONS
    garch = load_garch_predictions(horizons)
    if garch.is_empty():
        logger.warning("[figures] sin datos de GARCH, se omite fig_garch_volatility")
        return

    fig, axes = plt.subplots(len(horizons), 1, figsize=(11, 3.2 * len(horizons)), sharex=True)
    if len(horizons) == 1:
        axes = [axes]

    for ax, h in zip(axes, horizons):
        sub = garch.filter(pl.col("horizon") == h).sort("date")
        dates = sub["date"].to_list()
        ax.plot(dates, sub["realized_vol"].to_list(), color=COLOR_REAL, linewidth=1.0, label="Volatilidad realizada")
        ax.plot(
            dates, sub["predicted_vol"].to_list(), color=COLOR_PRED, linewidth=1.2, label="Volatilidad predicha (GARCH)"
        )
        ax.set_title(f"Horizonte {h} día{'s' if h > 1 else ''}", fontsize=10, loc="left")
        ax.tick_params(labelsize=8)

    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("GARCH(1,1) t-Student — volatilidad predicha vs. realizada (val)", fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))

    out_path = FIGURES_DIR / "garch_volatility.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[figures] guardado {out_path}")


def generate_all(horizons: list[int] | None = None) -> None:
    horizons = horizons or HORIZONS
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig_rmse_comparison(horizons)
    for h in horizons:
        fig_predicted_vs_real_grid(h)
    fig_garch_volatility(horizons)


if __name__ == "__main__":
    generate_all()
