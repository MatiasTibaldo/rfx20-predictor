"""
Figuras nuevas para los capítulos 1 a 4 de la tesis (evaluación de dónde
sumar imágenes, seguimiento posterior a la conciliación de resultados del
Capítulo 5). Reutiliza los datos ya persistidos del proyecto y la misma
paleta categórica validada que ya usa ``evaluation/figures.py``.

Genera:
  - fig1_historia_rfx20.png        (Cap. 1 — serie completa con eventos macro)
  - fig2_acf_pacf.png              (Cap. 3.1.4 — correlograma real del log-retorno)
  - fig3_volatility_clustering.png (Cap. 3.2.4 — volatilidad realizada real)
  - fig4_particion_temporal.png    (Cap. 4.4 — línea de tiempo train/val/test)
  - fig5_correcciones_datos.png    (Cap. 4.2.4 — serie con las 3 correcciones anotadas)
  - fig6_fracdiff.png              (Cap. 4.3.4 — ADF p-value vs. d)
  - fig7_composicion_pesos.png     (Cap. 2.2 — evolución de pesos por componente)

Uso: uv run python -m scripts.plot_thesis_figures
"""

from __future__ import annotations

import datetime as dt

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from config.settings import settings
from storage.store import DuckDBStore
from scripts.fractional_diff_exploration import run_exploration

FIGURES_DIR = settings.PROJECT_ROOT / "docs" / "figures"

# Misma paleta categórica validada que evaluation/figures.py (referencias/palette.md).
COLOR_REAL = "#2a78d6"    # slot 1, azul
COLOR_PRED = "#eb6834"    # slot 2, naranja
COLOR_AQUA = "#1baf7a"    # slot 3, aqua
COLOR_NAIVE = "#898781"   # ink "muted" — referencia neutral
COLOR_TEXT = "#0b0b0b"
COLOR_GRID = "#e1e0d9"
CATEGORICAL = [COLOR_REAL, COLOR_PRED, COLOR_AQUA, "#c23b6b", "#7a5cc0", "#b8912f"]

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "axes.edgecolor": COLOR_NAIVE,
        "axes.labelcolor": COLOR_TEXT,
        "text.color": COLOR_TEXT,
        "xtick.color": COLOR_NAIVE,
        "ytick.color": COLOR_NAIVE,
        "grid.color": COLOR_GRID,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.size": 10,
    }
)

MACRO_EVENTS = [
    (dt.date(2019, 8, 12), "PASO 2019"),
    (dt.date(2023, 10, 9), "Cambio de base"),
    (dt.date(2023, 11, 21), "Balotaje 2023"),
    (dt.date(2024, 7, 15), "Fase 2 plan econ."),
    (dt.date(2025, 9, 8), "Lunes negro 2025"),
]

CORRECTIONS = [
    (dt.date(2019, 9, 25), "Composición corrupta\nsep-2019"),
    (dt.date(2023, 10, 9), "Cambio de base\noct-2023"),
]


def load_index() -> pl.DataFrame:
    store = DuckDBStore()
    return store.load_parquet(layer="features", name="technical_index", version="v1").sort("date")


def fig1_historia_rfx20(idx: pl.DataFrame) -> None:
    dates = idx["date"].to_list()
    close = idx["close"].to_numpy()

    fig, ax = plt.subplots(figsize=(11, 5.0))
    ax.plot(dates, close, color=COLOR_REAL, linewidth=1.1)
    ax.set_yscale("log")
    ax.set_ylim(top=ax.get_ylim()[1] * 2.6)
    ax.set_ylabel("RFX20 (escala log)")
    ax.grid(color=COLOR_GRID, linewidth=0.6, which="both", alpha=0.6)

    ymax = ax.get_ylim()[1]
    levels = [0.94, 0.80, 0.66]
    for i, (date, label) in enumerate(MACRO_EVENTS):
        ax.axvline(date, color=COLOR_NAIVE, linestyle="--", linewidth=0.9, alpha=0.8, ymax=0.97)
        y = ymax * levels[i % len(levels)]
        ax.annotate(
            label, xy=(date, ax.get_ylim()[1] * 0.97), xytext=(date, y),
            ha="center", fontsize=8, color=COLOR_TEXT,
            arrowprops={"arrowstyle": "-", "color": COLOR_NAIVE, "lw": 0.7, "shrinkA": 0, "shrinkB": 2},
        )
    ax.set_title("Índice ROFEX 20 — serie completa (2018-2026)", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig1_historia_rfx20.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig2_acf_pacf(idx: pl.DataFrame) -> None:
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

    log_return = idx["log_return"].drop_nulls().to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    plot_acf(log_return, lags=20, ax=axes[0], color=COLOR_REAL, vlines_kwargs={"colors": COLOR_REAL})
    plot_pacf(log_return, lags=20, ax=axes[1], color=COLOR_PRED, vlines_kwargs={"colors": COLOR_PRED}, method="ywm")
    for ax, title in zip(axes, ["ACF", "PACF"]):
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Lag (ruedas)")
        ax.grid(color=COLOR_GRID, linewidth=0.6)
        for line in ax.lines:
            line.set_color(line.get_color())
    fig.suptitle("Correlograma del log-retorno diario del RFX20", fontsize=11, x=0.02, ha="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig2_acf_pacf.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig3_volatility_clustering(idx: pl.DataFrame) -> None:
    dates = idx["date"].to_list()
    realized_vol = idx["realized_vol_20"].to_numpy()

    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(dates, realized_vol, color=COLOR_AQUA, linewidth=0.9)
    ax.set_ylabel("Volatilidad realizada (20 ruedas)")
    ax.grid(color=COLOR_GRID, linewidth=0.6)
    ax.set_title("Agrupamiento de volatilidad — RFX20", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig3_volatility_clustering.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig4_particion_temporal() -> None:
    train_start, train_end = dt.date(2018, 4, 3), dt.date(2025, 1, 28)
    val_start, val_end = dt.date(2025, 1, 29), dt.date(2026, 4, 17)
    test_start, test_end = dt.date(2026, 4, 20), dt.date(2026, 8, 25)

    segments = [
        ("Train\n85%", train_start, train_end, COLOR_REAL),
        ("Val\n15%", val_start, val_end, COLOR_PRED),
        ("Test\n(nuevo)", test_start, test_end, COLOR_AQUA),
    ]

    fig, ax = plt.subplots(figsize=(11, 3.2))
    y = 0.5
    for label, start, end, color in segments:
        width = (mdates.date2num(end) - mdates.date2num(start))
        ax.barh(y, width, left=mdates.date2num(start), height=0.5, color=color, align="center")

    # Etiquetas de segmento arriba de la barra, con línea guía (el tramo de
    # test es demasiado angosto —86 días sobre 8 años— para texto interno).
    label_levels = [1.55, 1.15, 1.55]
    for (label, start, end, _), ylevel in zip(segments, label_levels):
        mid = mdates.date2num(start) + (mdates.date2num(end) - mdates.date2num(start)) / 2
        ax.annotate(
            label.replace("\n", " "), xy=(mid, 0.78), xytext=(mid, ylevel),
            ha="center", va="bottom", fontsize=9, color=COLOR_TEXT, fontweight="bold",
            arrowprops={"arrowstyle": "-", "color": COLOR_NAIVE, "lw": 0.8, "shrinkA": 0, "shrinkB": 2},
        )

    # Fechas de borde: los dos "empalmes" (train/val, val/test) son de solo
    # unos pocos días — a esta escala de varios años, mostrar cada fecha por
    # separado las superpone, así que cada empalme se etiqueta una sola vez.
    boundary_labels = [
        (train_start, "2018-04-03"),
        (dt.date(2025, 1, 28), "2025-01-28 / 29"),
        (dt.date(2026, 4, 18), "2026-04-17 / 20"),
        (test_end, "2026-08-25"),
    ]
    for i, (d, text) in enumerate(boundary_labels):
        level = -0.35 if i % 2 == 0 else -0.70
        ax.annotate(
            text, xy=(mdates.date2num(d), 0.22), xytext=(mdates.date2num(d), level),
            ha="center", va="top", fontsize=7.5, color=COLOR_NAIVE,
            arrowprops={"arrowstyle": "-", "color": COLOR_GRID, "lw": 0.7, "shrinkA": 0, "shrinkB": 2},
        )

    ax.xaxis_date()
    ax.set_yticks([])
    ax.set_ylim(-1.0, 2.0)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_title("Particionamiento temporal del dataset de modelado", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig4_particion_temporal.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig5_correcciones_datos(idx: pl.DataFrame) -> None:
    dates = idx["date"].to_list()
    close = idx["close"].to_numpy()

    fig, ax = plt.subplots(figsize=(11, 4.0))
    ax.plot(dates, close, color=COLOR_REAL, linewidth=1.1)
    ax.set_yscale("log")
    ax.set_ylabel("RFX20 (escala log, ya corregido)")
    ax.grid(color=COLOR_GRID, linewidth=0.6, which="both", alpha=0.6)

    ymin, ymax = ax.get_ylim()
    for i, (date, label) in enumerate(CORRECTIONS):
        ax.axvline(date, color=COLOR_PRED, linestyle="-", linewidth=1.3, alpha=0.9)
        y = ymax * (0.75 if i % 2 == 0 else 0.45)
        ax.annotate(
            label, xy=(date, y), xytext=(10, 0), textcoords="offset points",
            fontsize=8.5, color=COLOR_PRED, fontweight="bold", va="center",
        )
    ax.set_title(
        "Serie reconstruida del RFX20 — puntos de corrección de calidad de datos",
        fontsize=11, loc="left",
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig5_correcciones_datos.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig6_fracdiff(idx: pl.DataFrame) -> None:
    log_price = pl.Series("log_close", idx["close"].log().to_numpy())
    results = run_exploration(log_price).to_pandas()

    fig, ax1 = plt.subplots(figsize=(8.5, 4.2))
    ax1.plot(results["d"], results["adf_pvalue"], color=COLOR_REAL, marker="o", markersize=3, linewidth=1.3, label="p-value ADF")
    ax1.axhline(0.05, color=COLOR_NAIVE, linestyle="--", linewidth=1.0)
    ax1.annotate("p = 0,05", xy=(0.02, 0.05), xytext=(0, 4), textcoords="offset points", fontsize=8, color=COLOR_NAIVE)
    ax1.set_xlabel("d (orden de diferenciación fraccional)")
    ax1.set_ylabel("p-value del test ADF", color=COLOR_REAL)
    ax1.tick_params(axis="y", labelcolor=COLOR_REAL)
    ax1.grid(color=COLOR_GRID, linewidth=0.6)

    d_min_row = results[results["stationary"]].sort_values("d").iloc[0] if results["stationary"].any() else None
    if d_min_row is not None:
        ax1.axvline(d_min_row["d"], color=COLOR_PRED, linestyle=":", linewidth=1.2)
        ax1.annotate(
            f"d mínimo estacionario = {d_min_row['d']:.2f}",
            xy=(d_min_row["d"], d_min_row["adf_pvalue"]), xytext=(10, 20), textcoords="offset points",
            fontsize=8.5, color=COLOR_PRED, fontweight="bold",
            arrowprops={"arrowstyle": "->", "color": COLOR_PRED, "lw": 0.8},
        )

    ax1.set_title("Diferenciación fraccional: estacionariedad vs. d", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig6_fracdiff.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig7_composicion_pesos() -> None:
    store = DuckDBStore()
    comp = store.load_parquet(layer="raw", name="rfx20_composition", version="v1")
    weighted = (
        comp.with_columns((pl.col("quantity") * pl.col("close")).alias("mkt_value"))
        .with_columns((pl.col("mkt_value") / pl.col("mkt_value").sum().over("date")).alias("weight"))
    )
    avg_weight = weighted.group_by("ticker").agg(pl.col("weight").mean().alias("avg_w")).sort("avg_w", descending=True)
    top5 = avg_weight.head(5)["ticker"].to_list()

    wide = (
        weighted.select("date", "ticker", "weight")
        .filter(pl.col("ticker").is_in(top5))
        .pivot(values="weight", index="date", on="ticker")
        .sort("date")
        .fill_null(0.0)
    )
    other = (
        weighted.select("date", "ticker", "weight")
        .filter(~pl.col("ticker").is_in(top5))
        .group_by("date").agg(pl.col("weight").sum().alias("Otros"))
    )
    wide = wide.join(other, on="date", how="left").fill_null(0.0).sort("date")

    dates = wide["date"].to_list()
    cols = top5 + ["Otros"]
    colors = CATEGORICAL[: len(top5)] + [COLOR_GRID]
    values = [wide[c].to_numpy() for c in cols]

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.stackplot(dates, values, labels=cols, colors=colors, edgecolor="white", linewidth=0.3)
    ax.set_ylabel("Peso en el índice")
    ax.set_ylim(0, 1)
    ax.grid(color=COLOR_GRID, linewidth=0.6, axis="y")
    ax.legend(loc="upper left", fontsize=8, ncol=6, frameon=False, bbox_to_anchor=(0, 1.15))
    ax.set_title("Evolución de la composición del RFX20 — top 5 por peso promedio", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "fig7_composicion_pesos.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    idx = load_index()
    fig1_historia_rfx20(idx)
    fig2_acf_pacf(idx)
    fig3_volatility_clustering(idx)
    fig4_particion_temporal()
    fig5_correcciones_datos(idx)
    fig6_fracdiff(idx)
    fig7_composicion_pesos()
    print(f"Guardadas en {FIGURES_DIR}")


if __name__ == "__main__":
    main()
