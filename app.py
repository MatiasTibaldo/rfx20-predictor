"""
RFX20 Pipeline Monitor — Streamlit application.

Two sections:
  1. Pipeline: visual status of each pipeline node with one-click execution.
  2. Data Validation: exploratory views for the RFX20 index and OHLCV series.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import polars as pl
from scipy import stats as sp_stats
import streamlit as st
from plotly.subplots import make_subplots

from ingestion.composition import RFX20CompositionLoader
from storage.store import DuckDBStore

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="RFX20 Pipeline Monitor",
    page_icon="📈",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parent
_STATE_PATH = _ROOT / "results" / "pipeline_state.json"
_RAW_V1 = _ROOT / "data" / "raw" / "v1"
_COMPOSITION_BASE = _ROOT / "data" / "raw" / "rfx20_composition"

_PLOTLY_CONFIG: dict = {"displayModeBar": True, "scrollZoom": True}

_DEFAULT_STATE: dict = {
    "nodes": {
        "composition": {"status": "pending"},
        "ohlcv": {"status": "pending"},
        "processing": {"status": "pending"},
        "features": {"status": "pending"},
        "models": {"status": "pending"},
    }
}

_NODES: list[dict] = [
    {
        "key": "composition",
        "label": "1. Composición RFX20",
        "description": "Carga composición histórica, spot y dividendos desde CSVs crudos.",
        "cmd": [sys.executable, "-m", "ingestion.composition_runner"],
    },
    {
        "key": "ohlcv",
        "label": "2. Series OHLCV",
        "description": "Descarga OHLCV para los 20 tickers del índice (2018 → hoy).",
        "cmd": [sys.executable, "-m", "ingestion.pipeline_runner"],
    },
    {
        "key": "processing",
        "label": "3. Procesamiento",
        "description": "Limpieza, normalización y split train/val/test.",
        "cmd": [sys.executable, "-m", "processing.runner"],
    },
    {
        "key": "features",
        "label": "4. Feature Engineering",
        "description": "Indicadores técnicos, variables macro y features de calendario.",
        "cmd": [sys.executable, "-m", "features.runner"],
    },
    {
        "key": "models",
        "label": "5. Modelos",
        "description": "Entrenamiento y evaluación de modelos estadísticos, ML y DL.",
        "cmd": [sys.executable, "-m", "models.runner"],
    },
]

_STATUS_COLOR = {
    "completed": "#2ecc71",
    "running": "#3498db",
    "error": "#e74c3c",
    "pending": "#95a5a6",
}

_STATUS_LABEL = {
    "completed": "✅ Completado",
    "running": "⏳ Ejecutando",
    "error": "❌ Error",
    "pending": "⬜ Pendiente",
}

# 27-color palette for stacked area charts
_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
    "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
    "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
    "#5254a3", "#b5cf6b",
]

# ---------------------------------------------------------------------------
# Pipeline state helpers
# ---------------------------------------------------------------------------


def load_pipeline_state() -> dict:
    if _STATE_PATH.exists():
        try:
            return json.loads(_STATE_PATH.read_text())
        except Exception:
            pass
    return _DEFAULT_STATE.copy()


def save_pipeline_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def launch_node(node: dict) -> None:
    """Launch a pipeline node as a non-blocking subprocess and mark it running."""
    state = load_pipeline_state()
    state["nodes"][node["key"]]["status"] = "running"
    save_pipeline_state(state)
    subprocess.Popen(node["cmd"], cwd=str(_ROOT))
    st.rerun()


# ---------------------------------------------------------------------------
# Data loading helpers (cached)
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def load_rfx20_spot() -> pl.DataFrame | None:
    path = _RAW_V1 / "rfx20_spot.parquet"
    if not path.exists():
        return None
    return pl.read_parquet(path)


@st.cache_data(ttl=300)
def load_rfx20_divisor() -> pl.DataFrame | None:
    path = _RAW_V1 / "rfx20_divisor.parquet"
    if path.exists():
        return pl.read_parquet(path)
    try:
        loader = RFX20CompositionLoader()
        store = DuckDBStore()
        df = loader.load_divisors(_COMPOSITION_BASE)
        store.save_parquet(df, layer="raw", name="rfx20_divisor", version="v1")
        return df
    except Exception:
        return None


@st.cache_data(ttl=300)
def load_rfx20_composition() -> pl.DataFrame | None:
    path = _RAW_V1 / "rfx20_composition.parquet"
    if not path.exists():
        return None
    return pl.read_parquet(path)


@st.cache_data(ttl=300)
def load_ohlcv_ticker(ticker: str) -> pl.DataFrame | None:
    path = _RAW_V1 / f"{ticker.lower()}_ohlcv.parquet"
    if not path.exists():
        return None
    return pl.read_parquet(path)


@st.cache_data(ttl=300)
def list_ohlcv_tickers() -> list[str]:
    if not _RAW_V1.exists():
        return []
    return sorted(
        p.stem.replace("_ohlcv", "").upper()
        for p in _RAW_V1.glob("*_ohlcv.parquet")
    )


@st.cache_data(ttl=300)
def build_ohlcv_stats(tickers: list[str]) -> pd.DataFrame:
    """Per-ticker statistics table; uses business-day range for gap detection."""
    rows = []
    for ticker in tickers:
        df = load_ohlcv_ticker(ticker)
        if df is None:
            continue

        date_min = df["date"].min()
        date_max = df["date"].max()
        total_rows = len(df)
        expected_bdays = len(pd.bdate_range(start=str(date_min), end=str(date_max)))

        rows.append(
            {
                "ticker": ticker,
                "registros": total_rows,
                "fecha_min": str(date_min),
                "fecha_max": str(date_max),
                "días_cobertura": expected_bdays,
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def build_coverage_matrix(tickers: list[str]) -> pd.DataFrame:
    """Row per ticker, column per year; value = % of days vs market max that year."""
    years = list(range(2018, 2027))
    data: dict[str, dict[int, int]] = {}

    for ticker in tickers:
        df = load_ohlcv_ticker(ticker)
        if df is None:
            data[ticker] = {y: 0 for y in years}
            continue
        df_pd = df.select("date").to_pandas()
        df_pd["year"] = pd.to_datetime(df_pd["date"]).dt.year
        year_counts = df_pd["year"].value_counts().to_dict()
        data[ticker] = {y: int(year_counts.get(y, 0)) for y in years}

    matrix = pd.DataFrame(data).T
    matrix.columns = pd.Index(years)
    col_max = matrix.max().replace(0, 1)
    return (matrix.div(col_max) * 100).round(1)


@st.cache_data(ttl=300)
def load_all_returns(tickers: list[str], period: str) -> pd.DataFrame:
    """Daily returns (%) for all tickers over the requested period."""
    today = date.today()
    period_cutoffs: dict[str, date] = {
        "1Y": (pd.Timestamp(today) - pd.DateOffset(years=1)).date(),
        "3Y": (pd.Timestamp(today) - pd.DateOffset(years=3)).date(),
        "MAX": date(2018, 1, 1),
    }
    start_date = period_cutoffs.get(period, date(2018, 1, 1))

    returns: dict[str, pd.Series] = {}
    for ticker in tickers:
        df = load_ohlcv_ticker(ticker)
        if df is None or df.is_empty():
            continue
        df_f = df.filter(pl.col("date") >= pl.lit(start_date)).sort("date")
        if len(df_f) < 10:
            continue
        closes = df_f["close"].to_list()
        dates = df_f["date"].to_list()
        ret = [
            (closes[i] / closes[i - 1] - 1) * 100 if closes[i - 1] else None
            for i in range(1, len(closes))
        ]
        returns[ticker] = pd.Series(ret, index=dates[1:], dtype="float64")

    if not returns:
        return pd.DataFrame()
    return pd.DataFrame(returns).dropna(how="all")


@st.cache_data(ttl=300)
def load_all_returns_range(
    tickers: list[str], date_from: date, date_to: date
) -> pd.DataFrame:
    """Daily returns (%) for all tickers between date_from and date_to."""
    returns: dict[str, pd.Series] = {}
    for ticker in tickers:
        df = load_ohlcv_ticker(ticker)
        if df is None or df.is_empty():
            continue
        df_f = (
            df.filter(
                (pl.col("date") >= pl.lit(date_from)) & (pl.col("date") <= pl.lit(date_to))
            )
            .sort("date")
        )
        if len(df_f) < 10:
            continue
        closes = df_f["close"].to_list()
        dates = df_f["date"].to_list()
        ret = [
            (closes[i] / closes[i - 1] - 1) * 100 if closes[i - 1] else None
            for i in range(1, len(closes))
        ]
        returns[ticker] = pd.Series(ret, index=dates[1:], dtype="float64")
    if not returns:
        return pd.DataFrame()
    return pd.DataFrame(returns).dropna(how="all")


@st.cache_data(ttl=300)
def get_ticker_returns_range(
    ticker: str, date_from: date, date_to: date
) -> tuple[list, list]:
    """(dates, return_pcts) for a single ticker between date_from and date_to."""
    df = load_ohlcv_ticker(ticker)
    if df is None or df.is_empty():
        return [], []
    df_f = (
        df.filter(
            (pl.col("date") >= pl.lit(date_from)) & (pl.col("date") <= pl.lit(date_to))
        )
        .sort("date")
    )
    if len(df_f) < 2:
        return [], []
    closes = df_f["close"].to_list()
    dates = df_f["date"].to_list()
    pairs = [
        (dates[i], (closes[i] / closes[i - 1] - 1) * 100)
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    if not pairs:
        return [], []
    d, r = zip(*pairs)
    return list(d), list(r)


# ---------------------------------------------------------------------------
# Visualisation helpers
# ---------------------------------------------------------------------------


def _range_filter(df: pl.DataFrame, range_label: str) -> pl.DataFrame:
    today = date.today()
    cutoffs = {
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
    }
    if range_label == "MAX":
        return df
    cutoff_date = (pd.Timestamp(today) - cutoffs[range_label]).date()
    return df.filter(pl.col("date") >= pl.lit(cutoff_date))


def fig_spot_line(
    df: pl.DataFrame,
    range_label: str,
    div_df: pl.DataFrame | None = None,
) -> go.Figure:
    filtered = _range_filter(df, range_label)
    div_filtered = _range_filter(div_df, range_label) if div_df is not None else None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=filtered["date"].to_list(),
            y=filtered["value"].to_list(),
            mode="lines",
            line=dict(color="#3498db", width=1.5),
            name="Valor índice",
            hovertemplate="%{x}: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    if div_filtered is not None and not div_filtered.is_empty():
        fig.add_trace(
            go.Scatter(
                x=div_filtered["date"].to_list(),
                y=div_filtered["divisor"].to_list(),
                mode="lines",
                line=dict(color="#ff7f0e", width=1.2, dash="dot"),
                name="Divisor",
                opacity=0.8,
                hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.update_layout(
        title="Evolución del índice RFX20",
        xaxis_title="Fecha",
        hovermode="x unified",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    fig.update_yaxes(title_text="Valor índice (ARS)", secondary_y=False)
    fig.update_yaxes(title_text="Divisor", secondary_y=True, showgrid=False)
    return fig


def fig_composition_heatmap(comp_df: pl.DataFrame) -> go.Figure:
    df = comp_df.with_columns(
        pl.col("date")
        .dt.year()
        .cast(pl.Utf8)
        .add(pl.lit("-Q"))
        .add(pl.col("date").dt.quarter().cast(pl.Utf8))
        .alias("quarter")
    )

    tickers = sorted(df["ticker"].unique().to_list())
    quarters = sorted(df["quarter"].unique().to_list())

    presence = {t: {q: 0 for q in quarters} for t in tickers}
    for row in df.iter_rows(named=True):
        presence[row["ticker"]][row["quarter"]] = 1

    z = [[presence[t][q] for q in quarters] for t in tickers]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=quarters,
            y=tickers,
            colorscale=[[0, "#ecf0f1"], [1, "#2980b9"]],
            showscale=False,
            hoverongaps=False,
            hovertemplate="Ticker: %{y}<br>Período: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Presencia en el índice por trimestre",
        height=max(300, len(tickers) * 20),
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=-45),
    )
    return fig


def fig_weight_history(comp_df: pl.DataFrame) -> go.Figure:
    """Stacked area chart: each ticker's % weight in the index, aggregated by quarter."""
    df = comp_df.with_columns(
        (pl.col("close").fill_null(0.0) * pl.col("quantity").fill_null(0.0)).alias("mktcap")
    )
    total_by_date = df.group_by("date").agg(pl.col("mktcap").sum().alias("total_mktcap"))
    df = (
        df.join(total_by_date, on="date")
        .filter(pl.col("total_mktcap") > 0)
        .with_columns(
            (pl.col("mktcap") / pl.col("total_mktcap") * 100).alias("weight")
        )
        .with_columns(
            pl.col("date")
            .dt.year()
            .cast(pl.Utf8)
            .add(pl.lit("-Q"))
            .add(pl.col("date").dt.quarter().cast(pl.Utf8))
            .alias("quarter")
        )
    )

    quarterly = (
        df.group_by(["quarter", "ticker"])
        .agg(pl.col("weight").mean().alias("weight"))
        .sort("quarter")
    )

    tickers = sorted(df["ticker"].unique().to_list())
    quarters = sorted(quarterly["quarter"].unique().to_list())

    weight_map: dict[str, dict[str, float]] = {}
    for row in quarterly.iter_rows(named=True):
        weight_map.setdefault(row["ticker"], {})[row["quarter"]] = row["weight"]

    fig = go.Figure()
    for i, ticker in enumerate(tickers):
        t_weights = weight_map.get(ticker, {})
        weights = [t_weights.get(q, 0.0) for q in quarters]
        color = _PALETTE[i % len(_PALETTE)]
        fig.add_trace(
            go.Scatter(
                x=quarters,
                y=weights,
                name=ticker,
                mode="lines",
                stackgroup="one",
                line=dict(width=0.5, color=color),
                fillcolor=color,
                hovertemplate=f"<b>{ticker}</b><br>%{{x}}<br>Peso: %{{y:.1f}}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Peso histórico de componentes en el índice (% trimestral)",
        xaxis_title="Período",
        yaxis_title="% del índice",
        yaxis=dict(range=[0, 100]),
        hovermode="x unified",
        height=450,
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis=dict(tickangle=-45),
    )
    return fig


def fig_coverage_heatmap(matrix: pd.DataFrame) -> go.Figure:
    """Heatmap: ticker (y) × year (x), color = % of max days in market that year."""
    tickers = list(matrix.index)
    years = [str(y) for y in matrix.columns]
    z = matrix.values.tolist()
    text = [[f"{v:.0f}%" if v > 0 else "" for v in row] for row in z]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=years,
            y=tickers,
            colorscale="RdYlGn",
            zmin=0,
            zmax=100,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 8},
            hovertemplate="Ticker: %{y}<br>Año: %{x}<br>Cobertura: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="% cobertura"),
        )
    )
    fig.update_layout(
        title="Mapa de cobertura temporal (% relativo al máximo del mercado ese año)",
        height=max(400, len(tickers) * 22 + 80),
        margin=dict(l=0, r=0, t=50, b=0),
        xaxis_title="Año",
        yaxis_title="Ticker",
    )
    return fig


def fig_candlestick(df: pl.DataFrame, ticker: str) -> go.Figure:
    """Single-panel candlestick: volume on secondary y-axis (bg, 0.3 opacity), price primary."""
    close = df["close"].to_list()
    open_ = df["open"].to_list()
    dates = df["date"].to_list()

    def _sma(series: list, n: int) -> list:
        return [None] * (n - 1) + [
            sum(series[i - n + 1 : i + 1]) / n for i in range(n - 1, len(series))
        ]

    ma20 = _sma(close, 20)
    ma50 = _sma(close, 50)
    vol_colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(close, open_)]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Volume in background — secondary y-axis
    if "volume" in df.columns:
        fig.add_trace(
            go.Bar(
                x=dates,
                y=df["volume"].to_list(),
                name="Volumen (der.)",
                marker_color=vol_colors,
                marker_line_width=0,
                opacity=0.3,
            ),
            secondary_y=True,
        )

    # Candlestick — primary y-axis
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=open_,
            high=df["high"].to_list(),
            low=df["low"].to_list(),
            close=close,
            name=f"{ticker} (izq.)",
            increasing_line_color="#26a69a",
            increasing_fillcolor="#26a69a",
            decreasing_line_color="#ef5350",
            decreasing_fillcolor="#ef5350",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ma20,
            mode="lines",
            line=dict(color="#f5a623", width=1.2),
            name="MA20",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=ma50,
            mode="lines",
            line=dict(color="#a78bfa", width=1.2),
            name="MA50",
        ),
        secondary_y=False,
    )

    _bg = "#131722"
    _grid = "rgba(255,255,255,0.06)"
    fig.update_layout(
        title=f"{ticker} — Velas OHLCV",
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor=_bg,
        plot_bgcolor=_bg,
        font=dict(color="#d1d4dc"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#d1d4dc")),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=_grid, showline=False, zeroline=False, color="#d1d4dc")
    fig.update_yaxes(
        gridcolor=_grid, showline=False, zeroline=False, color="#d1d4dc",
        title_text="Precio", secondary_y=False,
    )
    fig.update_yaxes(
        showgrid=False, showline=False, zeroline=False, color="#d1d4dc",
        title_text="Volumen", secondary_y=True,
    )
    return fig


def fig_returns_scatter(dates: list, returns: list, ticker: str) -> go.Figure:
    """Daily return scatter (75%) + distribution histogram (25%)."""
    colors = ["#2ecc71" if r >= 0 else "#e74c3c" for r in returns]

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "scatter"}, {"type": "histogram"}]],
        column_widths=[0.75, 0.25],
        subplot_titles=["Retorno diario (%)", "Distribución"],
        horizontal_spacing=0.04,
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=returns,
            mode="markers",
            marker=dict(color=colors, size=3, opacity=0.7),
            name="Retorno %",
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_shape(
        type="line",
        x0=0,
        x1=1,
        xref="x domain",
        y0=0,
        y1=0,
        yref="y",
        line=dict(dash="dash", color="rgba(200,200,200,0.5)", width=1),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Histogram(
            y=returns,
            nbinsy=50,
            marker_color="#3498db",
            opacity=0.75,
            showlegend=False,
            hovertemplate="Retorno: %{y:.2f}%<br>Frecuencia: %{x}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title=f"{ticker} — Variación diaria (%)",
        height=380,
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
        hovermode="closest",
    )

    return fig


def _colored_metric(label: str, value: str, alert: bool) -> str:
    """HTML metric card; red background when alert=True."""
    bg = "#fde8e8" if alert else "#f0fdf4"
    color = "#7f1d1d" if alert else "#14532d"
    border = "#fca5a5" if alert else "#86efac"
    return (
        f"<div style='background:{bg};border:1px solid {border};"
        f"padding:10px 14px;border-radius:6px;text-align:center;'>"
        f"<p style='font-size:11px;color:#6b7280;margin:0 0 4px 0;'>{label}</p>"
        f"<p style='font-size:20px;font-weight:700;color:{color};margin:0;'>{value}</p>"
        f"</div>"
    )


def fig_violin_all_tickers(df_returns: pd.DataFrame, period: str) -> go.Figure:
    """Violin + boxplot for every ticker; one colour per ticker from _PALETTE."""
    fig = go.Figure()
    tickers = sorted(df_returns.columns.tolist())

    for i, ticker in enumerate(tickers):
        vals = df_returns[ticker].dropna().tolist()
        if not vals:
            continue
        arr = np.array(vals)
        med = float(np.median(arr))
        std = float(np.std(arr, ddof=1))
        mn = float(arr.min())
        mx = float(arr.max())
        color = _PALETTE[i % len(_PALETTE)]

        fig.add_trace(
            go.Violin(
                x=[ticker] * len(vals),
                y=vals,
                name=ticker,
                box_visible=True,
                meanline_visible=True,
                line_color=color,
                fillcolor=color,
                opacity=0.55,
                showlegend=False,
                hovertemplate=(
                    f"<b>{ticker}</b><br>"
                    f"Mediana: {med:.3f}%<br>"
                    f"Desvío: {std:.3f}%<br>"
                    f"Mín: {mn:.3f}%<br>"
                    f"Máx: {mx:.3f}%<extra></extra>"
                ),
            )
        )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(200,200,200,0.45)",
        line_width=1,
    )
    fig.update_layout(
        title=f"Distribución de retornos diarios por ticker — {period}",
        xaxis_title="Ticker",
        yaxis_title="Retorno diario (%)",
        showlegend=False,
        height=500,
        margin=dict(l=0, r=0, t=50, b=0),
        hovermode="closest",
    )
    return fig


def fig_rolling_volatility(df: pl.DataFrame, ticker: str, window: int) -> go.Figure:
    """Price (top) + rolling annualised volatility % (bottom), dark theme."""
    df_s = df.sort("date")
    closes = df_s["close"].to_list()
    dates = df_s["date"].to_list()

    rets = [None] + [
        (closes[i] / closes[i - 1] - 1) if closes[i - 1] else None
        for i in range(1, len(closes))
    ]

    vol: list[float | None] = []
    for i in range(len(rets)):
        if i < window:
            vol.append(None)
            continue
        window_rets = [r for r in rets[i - window + 1 : i + 1] if r is not None]
        vol.append(
            float(np.std(window_rets, ddof=1) * np.sqrt(252) * 100)
            if len(window_rets) >= 2
            else None
        )

    valid_vols = [v for v in vol if v is not None]
    mean_vol = float(np.mean(valid_vols)) if valid_vols else 0.0

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.5, 0.5],
        vertical_spacing=0.03,
        subplot_titles=[
            f"{ticker} — Precio de cierre",
            f"Volatilidad rolling {window}d (anualizada %)",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=closes,
            mode="lines",
            line=dict(color="#3498db", width=1.2),
            name="Precio",
            hovertemplate="%{x}: $%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=vol,
            mode="lines",
            fill="tozeroy",
            line=dict(color="#f5a623", width=1.2),
            fillcolor="rgba(245,166,35,0.20)",
            name=f"Vol {window}d",
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_hline(
        y=mean_vol,
        line_dash="dot",
        line_color="rgba(255,255,255,0.35)",
        line_width=1,
        annotation_text=f"Media: {mean_vol:.1f}%",
        annotation_position="top right",
        annotation_font=dict(color="#d1d4dc", size=10),
        row=2,
        col=1,
    )

    _bg = "#131722"
    _grid = "rgba(255,255,255,0.06)"
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor=_bg,
        plot_bgcolor=_bg,
        font=dict(color="#d1d4dc"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#d1d4dc")),
        hovermode="x unified",
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=_grid, showline=False, zeroline=False, color="#d1d4dc")
    fig.update_yaxes(gridcolor=_grid, showline=False, zeroline=False, color="#d1d4dc")
    fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
    return fig


def fig_distribution_individual(returns: list[float], ticker: str) -> go.Figure:
    """Violin+box (left) + histogram with normal PDF overlay (right)."""
    arr = np.array(returns)
    mean_v = float(arr.mean())
    std_v = float(arr.std(ddof=1))

    x_curve = np.linspace(arr.min(), arr.max(), 300)
    normal_pdf = sp_stats.norm.pdf(x_curve, mean_v, std_v)

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.35, 0.65],
        subplot_titles=["Violin + Boxplot", "Histograma vs. Distribución normal"],
        horizontal_spacing=0.08,
    )

    fig.add_trace(
        go.Violin(
            y=returns,
            name=ticker,
            box_visible=True,
            meanline_visible=True,
            line_color="#3498db",
            fillcolor="rgba(52,152,219,0.35)",
            showlegend=False,
            hovertemplate="Retorno: %{y:.3f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(200,200,200,0.4)",
        line_width=1,
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Histogram(
            x=returns,
            nbinsx=50,
            histnorm="probability density",
            marker_color="rgba(52,152,219,0.35)",
            marker_line=dict(color="rgba(52,152,219,0.7)", width=0.5),
            name="Histograma",
            showlegend=True,
            hovertemplate="Retorno: %{x:.3f}%<br>Densidad: %{y:.4f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Scatter(
            x=x_curve.tolist(),
            y=normal_pdf.tolist(),
            mode="lines",
            line=dict(color="#f5a623", width=2, dash="dash"),
            name=f"Normal (μ={mean_v:.2f}%, σ={std_v:.2f}%)",
            showlegend=True,
            hovertemplate="Retorno: %{x:.3f}%<br>Densidad teórica: %{y:.4f}<extra></extra>",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title=f"{ticker} — Distribución de retornos diarios",
        height=420,
        margin=dict(l=0, r=0, t=60, b=0),
        hovermode="closest",
        legend=dict(x=0.38, y=0.97, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(title_text="Retorno (%)", row=1, col=2)
    fig.update_yaxes(title_text="Densidad", row=1, col=2)
    fig.update_yaxes(title_text="Retorno (%)", row=1, col=1)
    return fig


def fig_multi_ticker(dfs: dict[str, pl.DataFrame], mode: str) -> go.Figure:
    ylabel = (
        "Precio normalizado (base 100)"
        if mode == "precio normalizado (base 100)"
        else "Retorno acumulado (%)"
    )
    fig = go.Figure()

    for ticker, df in dfs.items():
        if df is None or df.is_empty():
            continue
        dates = df["date"].to_list()
        prices = df["close"].to_list()
        if mode == "precio normalizado (base 100)":
            base = prices[0] if prices[0] else 1
            y = [p / base * 100 for p in prices]
        else:
            y = []
            cumret = 1.0
            for i, p in enumerate(prices):
                if i == 0:
                    y.append(0.0)
                elif prices[i - 1]:
                    cumret *= p / prices[i - 1]
                    y.append((cumret - 1) * 100)
                else:
                    y.append(y[-1] if y else 0.0)

        fig.add_trace(go.Scatter(x=dates, y=y, mode="lines", name=ticker))

    fig.update_layout(
        title="Comparación de tickers",
        yaxis_title=ylabel,
        xaxis_title="Fecha",
        hovermode="x unified",
        height=450,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar summary
# ---------------------------------------------------------------------------


def _render_sidebar_summary() -> None:
    tickers = list_ohlcv_tickers()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Resumen de datos")
    st.sidebar.markdown(f"**Tickers disponibles:** {len(tickers)}")

    if _RAW_V1.exists():
        parquets = list(_RAW_V1.glob("*.parquet"))
        if parquets:
            last_mtime = max(p.stat().st_mtime for p in parquets)
            last_dt = datetime.fromtimestamp(last_mtime)
            st.sidebar.markdown(f"**Último update:** {last_dt.strftime('%Y-%m-%d %H:%M')}")

    if tickers:
        with st.sidebar:
            with st.spinner("Cargando rango de fechas..."):
                stats = build_ohlcv_stats(tickers)
        if not stats.empty:
            d_min = stats["fecha_min"].min()
            d_max = stats["fecha_max"].max()
            st.sidebar.markdown(f"**Rango de fechas:** {d_min[:10]} → {d_max[:10]}")


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def render_pipeline_section() -> None:
    st.header("Estado del Pipeline")
    state = load_pipeline_state()
    nodes_state = state.get("nodes", {})

    if st.button("🔄 Actualizar estado"):
        st.cache_data.clear()
        st.rerun()

    for i, node in enumerate(_NODES):
        key = node["key"]
        ns = nodes_state.get(key, {"status": "pending"})
        status = ns.get("status", "pending")
        color = _STATUS_COLOR.get(status, "#95a5a6")
        status_label = _STATUS_LABEL.get(status, status)

        with st.container():
            col_indicator, col_info, col_btn = st.columns([0.05, 0.75, 0.2])

            with col_indicator:
                st.markdown(
                    f"<div style='width:16px;height:16px;border-radius:50%;"
                    f"background:{color};margin-top:8px;'></div>",
                    unsafe_allow_html=True,
                )

            with col_info:
                st.markdown(f"**{node['label']}**")
                st.caption(node["description"])
                st.caption(f"Estado: {status_label}")

                if status == "completed" and ns.get("stats"):
                    with st.expander("Ver estadísticas"):
                        st.json(ns["stats"])

                if status == "error" and ns.get("error"):
                    st.error(f"Error: {ns['error']}")

            with col_btn:
                prev_completed = (
                    i == 0
                    or nodes_state.get(_NODES[i - 1]["key"], {}).get("status") == "completed"
                )
                can_run = prev_completed and status not in ("running", "completed")
                if can_run:
                    if st.button("▶ Ejecutar", key=f"run_{key}", type="primary"):
                        launch_node(node)

        st.divider()


def render_rfx20_tab() -> None:
    spot_df = load_rfx20_spot()
    comp_df = load_rfx20_composition()
    divisor_df = load_rfx20_divisor()

    if spot_df is None:
        st.info("Parquet rfx20_spot no encontrado. Ejecutar el nodo de Composición primero.")
        return

    # --- Summary metrics ---
    date_min = spot_df["date"].min()
    date_max = spot_df["date"].max()
    val_min = float(spot_df["value"].min())
    val_max = float(spot_df["value"].max())
    n_days = len(spot_df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Fecha inicio", str(date_min))
    c2.metric("Fecha fin", str(date_max))
    c3.metric("Días con datos", f"{n_days:,}")
    c4.metric("Mínimo histórico", f"{val_min:,.2f}")
    c5.metric("Máximo histórico", f"{val_max:,.2f}")
    if divisor_df is not None and not divisor_df.is_empty():
        current_divisor = float(divisor_df["divisor"].tail(1)[0])
        c6.metric(
            "Divisor actual",
            f"{current_divisor:,.0f}",
            help=(
                "El divisor es un factor de ajuste que mantiene la continuidad "
                "del índice ante eventos corporativos como splits, dividendos o "
                "cambios en la composición. Un divisor creciente indica ajustes "
                "acumulados que reducen el valor calculado del índice."
            ),
        )

    # --- Spot line chart ---
    st.subheader("Evolución del índice")
    range_options = ["3M", "6M", "1Y", "3Y", "MAX"]
    selected_range = st.radio(
        "Rango",
        range_options,
        index=4,
        horizontal=True,
        key="spot_range",
    )
    st.plotly_chart(
        fig_spot_line(spot_df, selected_range, divisor_df),
        use_container_width=True,
        config=_PLOTLY_CONFIG,
    )

    if comp_df is None:
        st.info("Parquet rfx20_composition no encontrado.")
        return

    # --- Composition presence heatmap ---
    st.subheader("Composición histórica del índice")
    st.plotly_chart(
        fig_composition_heatmap(comp_df),
        use_container_width=True,
        config=_PLOTLY_CONFIG,
    )

    # --- Weight history stacked area ---
    if "close" in comp_df.columns and "quantity" in comp_df.columns:
        st.subheader("Peso histórico de componentes")
        with st.spinner("Calculando pesos históricos..."):
            st.plotly_chart(
                fig_weight_history(comp_df),
                use_container_width=True,
                config=_PLOTLY_CONFIG,
            )
    else:
        st.info("Columnas 'close' o 'quantity' no disponibles en rfx20_composition.")

    # --- Composition at date ---
    st.subheader("Composición en una fecha específica")
    comp_date_min = comp_df["date"].min()
    comp_date_max = comp_df["date"].max()
    selected_date = st.date_input(
        "Seleccionar fecha",
        value=comp_date_max,
        min_value=comp_date_min,
        max_value=comp_date_max,
        key="comp_date",
    )

    filtered = comp_df.filter(pl.col("date") <= pl.lit(selected_date))
    if filtered.is_empty():
        st.warning("No hay datos para esa fecha.")
    else:
        resolved_date = filtered["date"].max()
        if resolved_date != selected_date:
            st.caption(
                f"Fecha exacta no disponible, mostrando la más reciente: {resolved_date}"
            )

        day_df = comp_df.filter(pl.col("date") == resolved_date)

        if "close" in day_df.columns:
            total_value = day_df["close"].fill_null(0).dot(
                day_df["quantity"].fill_null(0)
            )
            if total_value and total_value > 0:
                day_df = day_df.with_columns(
                    (
                        pl.col("close").fill_null(0)
                        * pl.col("quantity").fill_null(0)
                        / total_value
                        * 100
                    )
                    .round(2)
                    .alias("peso_est_%")
                )

        st.dataframe(day_df.to_pandas(), use_container_width=True)


def render_ohlcv_tab() -> None:
    tickers = list_ohlcv_tickers()

    if not tickers:
        st.info("No se encontraron archivos *_ohlcv.parquet en data/raw/v1/.")
        return

    # --- Stats table ---
    st.subheader("Estadísticas por ticker")
    with st.spinner("Calculando estadísticas..."):
        stats_df = build_ohlcv_stats(tickers)

    if not stats_df.empty:

        def _highlight(row: pd.Series) -> list[str]:
            return ["background-color: #f8f9fa; color: #1a1a1a;"] * len(row)

        st.dataframe(
            stats_df.style.apply(_highlight, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No se pudieron calcular estadísticas.")

    st.divider()

    # --- Candlestick ---
    st.subheader("Gráfico de velas")
    col_l, col_r = st.columns([0.3, 0.7])
    df_raw: pl.DataFrame | None = None
    date_range: tuple = ()

    with col_l:
        ticker_candle = st.selectbox("Ticker (velas)", tickers, key="candle_ticker")
        df_raw = load_ohlcv_ticker(ticker_candle)
        if df_raw is not None and not df_raw.is_empty():
            d_min = df_raw["date"].min()
            d_max = df_raw["date"].max()
            date_range = st.date_input(
                "Rango de fechas",
                value=(d_min, d_max),
                min_value=d_min,
                max_value=d_max,
                key="candle_range",
            )

    with col_r:
        if df_raw is not None and not df_raw.is_empty() and len(date_range) == 2:
            df_candle = df_raw.filter(
                (pl.col("date") >= pl.lit(date_range[0]))
                & (pl.col("date") <= pl.lit(date_range[1]))
            )
            if not df_candle.is_empty():
                st.plotly_chart(
                    fig_candlestick(df_candle, ticker_candle),
                    use_container_width=True,
                    config=_PLOTLY_CONFIG,
                )
            else:
                st.info("Sin datos en el rango seleccionado.")
        elif df_raw is None:
            st.warning(f"Sin datos para {ticker_candle}.")

    st.divider()

    # --- Daily returns scatter + histogram ---
    st.subheader("Variación diaria (%)")
    ticker_ret = st.selectbox("Ticker (retornos)", tickers, key="ret_ticker")
    df_ret_raw = load_ohlcv_ticker(ticker_ret)

    if df_ret_raw is not None and not df_ret_raw.is_empty():
        df_sorted = df_ret_raw.sort("date")
        closes = df_sorted["close"].to_list()
        dates_all = df_sorted["date"].to_list()

        ret_pairs = [
            (dates_all[i], (closes[i] / closes[i - 1] - 1) * 100)
            for i in range(1, len(closes))
            if closes[i - 1]
        ]

        if ret_pairs:
            ret_dates, ret_vals = zip(*ret_pairs)
            ret_dates = list(ret_dates)
            ret_vals = list(ret_vals)

            arr = np.array(ret_vals)
            mean_v = float(np.mean(arr))
            std_v = float(np.std(arr))
            s = pd.Series(arr)
            skew_v = float(s.skew())
            kurt_v = float(s.kurtosis())

            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric(
                "Media",
                f"{mean_v:.3f}%",
                help=(
                    "Promedio de las variaciones diarias en el período. "
                    "Un valor positivo indica tendencia alcista promedio."
                ),
            )
            mc2.metric(
                "Desvío estándar",
                f"{std_v:.3f}%",
                help=(
                    "Mide la dispersión de los retornos. "
                    "Valores altos indican mayor volatilidad e incertidumbre."
                ),
            )
            mc3.metric(
                "Skewness",
                f"{skew_v:.3f}",
                help=(
                    "Asimetría de la distribución. Valores negativos indican "
                    "que las caídas tienden a ser más extremas que las subidas."
                ),
            )
            mc4.metric(
                "Kurtosis (exceso)",
                f"{kurt_v:.3f}",
                help=(
                    "Mide el peso de las colas. Valores mayores a 3 indican que "
                    "los eventos extremos ocurren más de lo esperado en una "
                    "distribución normal (colas pesadas)."
                ),
            )

            st.plotly_chart(
                fig_returns_scatter(ret_dates, ret_vals, ticker_ret),
                use_container_width=True,
                config=_PLOTLY_CONFIG,
            )
        else:
            st.warning("No hay retornos calculables para este ticker.")
    else:
        st.warning(f"Sin datos para {ticker_ret}.")

    st.divider()

    # --- Returns analysis: 3 sub-tabs ---
    st.subheader("Análisis estadístico de retornos")
    tab_violin, tab_dist = st.tabs(
        ["Violín por ticker", "Distribución individual"]
    )

    with tab_violin:
        _today = date.today()
        _default_from = (pd.Timestamp(_today) - pd.DateOffset(years=1)).date()
        vc_a, vc_b = st.columns(2)
        with vc_a:
            violin_from = st.date_input(
                "Desde", value=_default_from, max_value=_today, key="violin_from"
            )
        with vc_b:
            violin_to = st.date_input(
                "Hasta", value=_today, max_value=_today, key="violin_to"
            )
        with st.spinner("Cargando retornos..."):
            df_violin_ret = load_all_returns_range(tickers, violin_from, violin_to)
        if df_violin_ret.empty:
            st.info("No hay datos de retornos disponibles para el rango seleccionado.")
        else:
            title_range = f"{violin_from} → {violin_to}"
            st.plotly_chart(
                fig_violin_all_tickers(df_violin_ret, title_range),
                use_container_width=True,
                config=_PLOTLY_CONFIG,
            )

    with tab_dist:
        dc1, dc2, dc3 = st.columns([0.22, 0.22, 0.56])
        with dc1:
            ticker_dist = st.selectbox("Ticker", tickers, key="dist_ticker")
        df_dist_raw = load_ohlcv_ticker(ticker_dist)
        if df_dist_raw is not None and not df_dist_raw.is_empty():
            d_min_d = df_dist_raw["date"].min()
            d_max_d = df_dist_raw["date"].max()
            with dc2:
                dist_from = st.date_input(
                    "Desde",
                    value=d_min_d,
                    min_value=d_min_d,
                    max_value=d_max_d,
                    key="dist_from",
                )
            with dc3:
                dist_to = st.date_input(
                    "Hasta",
                    value=d_max_d,
                    min_value=d_min_d,
                    max_value=d_max_d,
                    key="dist_to",
                )
            _, returns_dist = get_ticker_returns_range(ticker_dist, dist_from, dist_to)
            if returns_dist:
                arr_d = np.array(returns_dist)
                mean_d = float(arr_d.mean())
                std_d = float(arr_d.std(ddof=1))
                skew_d = float(pd.Series(arr_d).skew())
                kurt_d = float(pd.Series(arr_d).kurtosis())

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric(
                    "Media",
                    f"{mean_d:.3f}%",
                    help=(
                        "Retorno promedio diario en el período. "
                        "Multiplicado por 252 aproxima el retorno anual esperado."
                    ),
                )
                mc2.metric(
                    "Desvío estándar",
                    f"{std_d:.3f}%",
                    help=(
                        "Volatilidad diaria. Multiplicado por √252 da la volatilidad "
                        "anualizada, métrica estándar en finanzas."
                    ),
                )
                mc3.metric(
                    "Skewness",
                    f"{skew_d:.3f}",
                    delta="⚠ |sk| > 1" if abs(skew_d) > 1 else None,
                    delta_color="inverse",
                    help=(
                        "Asimetría. En acciones argentinas es común ver skewness negativo: "
                        "las caídas bruscas son más frecuentes que las subidas equivalentes."
                    ),
                )
                mc4.metric(
                    "Kurtosis (exceso)",
                    f"{kurt_d:.3f}",
                    delta="⚠ K > 3" if kurt_d > 3 else None,
                    delta_color="inverse",
                    help=(
                        "Exceso de kurtosis respecto a distribución normal (valor base = 0 "
                        "en convención de Fisher, o 3 en Pearson). Valores altos son la norma "
                        "en mercados emergentes e indican que los modelos que asumen normalidad "
                        "subestimarán el riesgo."
                    ),
                )

                st.plotly_chart(
                    fig_distribution_individual(returns_dist, ticker_dist),
                    use_container_width=True,
                    config=_PLOTLY_CONFIG,
                )
                st.info(
                    "La curva naranja representa una distribución normal teórica con la misma "
                    "media y desvío que los retornos observados. La distancia entre el "
                    "histograma y la curva revela qué tan alejados están los retornos reales "
                    "de la normalidad, algo crítico para la selección de modelos."
                )
            else:
                st.warning("No hay retornos calculables para el ticker/rango seleccionado.")
        else:
            st.warning(f"Sin datos para {ticker_dist}.")

    st.divider()

    # --- Multi-ticker comparison ---
    st.subheader("Comparación de tickers")
    selected_tickers = st.multiselect(
        "Seleccionar tickers (máx. 10)",
        tickers,
        default=tickers[:3] if len(tickers) >= 3 else tickers,
        max_selections=10,
        key="multi_tickers",
    )
    compare_mode = st.selectbox(
        "Modo de comparación",
        ["precio normalizado (base 100)", "retorno acumulado"],
        key="compare_mode",
    )
    if selected_tickers:
        dfs = {t: load_ohlcv_ticker(t) for t in selected_tickers}
        st.plotly_chart(
            fig_multi_ticker(dfs, compare_mode),
            use_container_width=True,
            config=_PLOTLY_CONFIG,
        )


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------


def main() -> None:
    st.title("RFX20 Pipeline Monitor")

    section = st.sidebar.radio(
        "Sección",
        ["Pipeline", "Validación de datos"],
        label_visibility="collapsed",
    )

    _render_sidebar_summary()

    if section == "Pipeline":
        render_pipeline_section()
    else:
        tab_rfx20, tab_ohlcv = st.tabs(["Índice RFX20", "Series OHLCV"])
        with tab_rfx20:
            render_rfx20_tab()
        with tab_ohlcv:
            render_ohlcv_tab()


if __name__ == "__main__":
    main()
