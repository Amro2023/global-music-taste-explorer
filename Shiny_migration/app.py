# Shiny_migration/app.py
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.express as px

from shiny import App, ui, render, reactive

# =========================
# Paths (repo-friendly)
# =========================
HERE = Path(__file__).resolve().parent
EXPORTS = HERE / "exports"

# =========================
# Data load (cached)
# =========================
@lru_cache(maxsize=1)
def data():
    """
    Returns (country_year_summary, top_tracks, artist_year)
    Cached via lru_cache (safe outside reactive context).
    """
    cys_path = EXPORTS / "country_year_summary.parquet"
    tt_path = EXPORTS / "top_tracks_country_year_top500.parquet"
    ay_path = EXPORTS / "artist_country_year_top200.parquet"

    if not cys_path.exists() or not tt_path.exists() or not ay_path.exists():
        missing = [str(p) for p in [cys_path, tt_path, ay_path] if not p.exists()]
        raise FileNotFoundError(
            "Missing parquet exports in Shiny_migration/exports.\n"
            "Missing:\n- " + "\n- ".join(missing) + "\n\n"
            "Fix: copy from repo root exports:\n"
            "cp -R ../exports/* exports/"
        )

    cys = pd.read_parquet(cys_path)
    tt = pd.read_parquet(tt_path)
    ay = pd.read_parquet(ay_path)
    return cys, tt, ay


def kpi_card(label: str, value: str):
    return ui.div(
        ui.div(label, class_="kpi-label"),
        ui.div(value, class_="kpi-value"),
        class_="kpi-card",
    )


# =========================
# UI
# =========================
app_ui = ui.page_fluid(
    ui.tags.style(
        """
        body { background: #0b0f1a; color: #e8eefc; }
        .container-fluid { padding-top: 1.0rem; }

        /* Top header */
        .gme-title { font-size: 1.6rem; font-weight: 800; margin: 0; }
        .gme-sub { opacity: .75; margin-top: .2rem; }

        /* KPI cards */
        .kpi-row { display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 6px 0; }
        .kpi-card { background: #121a2b; border: 1px solid #1e2a44; padding: 12px 14px;
                    border-radius: 14px; min-width: 200px; }
        .kpi-label { font-size: 0.85rem; opacity: .8; }
        .kpi-value { font-size: 1.35rem; font-weight: 800; margin-top: 6px; }

        /* Panels */
        .panel { background: #0f1626; border: 1px solid #1e2a44; border-radius: 16px; padding: 14px; }
        .note { opacity: 0.75; font-size: 0.9rem; }

        /* Make plotly blend */
        .plotly { border-radius: 12px; overflow: hidden; }
        """
    ),

    ui.div(
        ui.h2("🎧 Global Music Taste Explorer (Shiny)", class_="gme-title"),
        ui.div("Same data exports as Streamlit — now running in Shiny for Python.", class_="gme-sub"),
        class_="panel",
    ),

    # ✅ IMPORTANT FIX: use nav_panel, not nav
    ui.navset_tab(
        ui.nav_panel(
            "🌍 World View",
            ui.div(
                ui.div(
                    ui.p(
                        "Choropleth shows total Spotify Top 200 streams by country for the selected year. "
                        "“Global” is excluded from the map.",
                        class_="note",
                    ),
                    ui.layout_columns(
                        ui.input_slider("wv_year", "Year", min=2017, max=2021, value=2020, step=1),
                        ui.input_switch("wv_log", "Log scale", value=True),
                        ui.input_numeric("wv_topn", "Top countries callout", value=10, min=3, max=25),
                        col_widths=[6, 3, 3],
                    ),
                    ui.output_ui("wv_kpis"),
                    ui.output_ui("wv_map"),
                    ui.hr(),
                    ui.h4(ui.output_text("wv_table_title")),
                    ui.output_data_frame("wv_top_table"),
                    class_="panel",
                )
            ),
        ),

        ui.nav_panel(
            "📊 Explorer",
            ui.div(
                ui.div(
                    ui.p(
                        "Pick a country and year to explore top songs. Keeping “Global” is useful as a worldwide benchmark.",
                        class_="note",
                    ),
                    ui.layout_columns(
                        ui.input_select("ex_country", "Country", choices=["Global"]),
                        ui.input_select("ex_year", "Year", choices=["2020"]),
                        col_widths=[8, 4],
                    ),
                    ui.input_slider("ex_topn", "Top N tracks", min=10, max=100, value=25, step=5),
                    ui.output_ui("ex_kpis"),
                    ui.output_ui("ex_bar"),
                    ui.output_ui("ex_table_expander"),
                    class_="panel",
                )
            ),
        ),

        ui.nav_panel(
            "📈 Trends",
            ui.div(
                ui.div(
                    ui.p(
                        "Select an artist, then choose countries to compare. Tip: include “Global” as a baseline.",
                        class_="note",
                    ),
                    ui.layout_columns(
                        ui.input_select("tr_artist", "Artist (Top 500 global)", choices=["(loading...)"]),
                        ui.input_selectize("tr_countries", "Countries", choices=[], multiple=True),
                        col_widths=[6, 6],
                    ),
                    ui.output_ui("tr_line"),
                    class_="panel",
                )
            ),
        ),

        id="tabs",
    ),
)


# =========================
# Server
# =========================
def server(input, output, session):
    # Load once (cached)
    @reactive.calc
    def cys():
        return data()[0]

    @reactive.calc
    def tt():
        return data()[1]

    @reactive.calc
    def ay():
        return data()[2]

    # Initialize dynamic choices once data is available
    @reactive.effect
    def _init_choices():
        _cys = cys()
        _tt = tt()
        _ay = ay()

        # Years (use cys for global)
        years = sorted(pd.Series(_cys["year"]).dropna().unique().tolist())
        if years:
            ui.update_slider("wv_year", min=min(years), max=max(years), value=max(years), session=session)
            ui.update_select("ex_year", choices=[str(y) for y in years], selected=str(max(years)), session=session)

        # Countries for Explorer
        countries = sorted(pd.Series(_tt["country"]).dropna().unique().tolist())
        if countries:
            selected = "Global" if "Global" in countries else countries[0]
            ui.update_select("ex_country", choices=countries, selected=selected, session=session)

        # Artists (top 500 global)
        top_artists = (
            _ay.groupby("artist_name")["streams_sum"].sum().sort_values(ascending=False).head(500).index.tolist()
        )
        if top_artists:
            ui.update_select("tr_artist", choices=top_artists, selected=top_artists[0], session=session)

    # -------------------------
    # WORLD VIEW
    # -------------------------
    @reactive.calc
    def wv_df_map():
        df = cys().copy()
        y = int(input.wv_year())
        df = df[(df["year"] == y) & (df["iso3"].notna()) & (df["country"] != "Global")].copy()
        df["color_val"] = df["total_streams"].clip(lower=1)
        if bool(input.wv_log()):
            df["color_val"] = np.log10(df["color_val"])
        return df

    @output
    @render.ui
    def wv_kpis():
        df = wv_df_map()
        if df.empty:
            return ui.div(ui.p("No map rows for this year.", class_="note"))
        return ui.div(
            kpi_card("Total Streams", f"{df['total_streams'].sum():,.0f}"),
            kpi_card("Countries", f"{df['country'].nunique():,}"),
            kpi_card("Unique Artists (sum)", f"{df['unique_artists'].sum():,.0f}"),
            class_="kpi-row",
        )

    @output
    @render.ui
    def wv_map():
        df = wv_df_map()
        y = int(input.wv_year())
        if df.empty:
            return ui.div(ui.p("No map data.", class_="note"))
        fig = px.choropleth(
            df,
            locations="iso3",
            color="color_val",
            hover_name="country",
            hover_data={
                "total_streams": ":,.0f",
                "unique_tracks": ":,",
                "unique_artists": ":,",
                "avg_rank": ":.2f",
                "iso3": False,
                "color_val": False,
            },
            color_continuous_scale="Viridis",
            title=f"Total Streams by Country — {y}",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=60, b=0))
        return ui.div(ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)), class_="plotly")

    @output
    @render.text
    def wv_table_title():
        return f"Top {int(input.wv_topn())} Countries (by total streams)"

    @output
    @render.data_frame
    def wv_top_table():
        df = wv_df_map()
        n = int(input.wv_topn())
        top_c = df.sort_values("total_streams", ascending=False).head(n)
        cols = ["country", "total_streams", "unique_artists", "unique_tracks"]
        return render.DataGrid(top_c[cols], height="320px")

    # -------------------------
    # EXPLORER
    # -------------------------
    @reactive.calc
    def ex_df():
        df = tt().copy()
        country = input.ex_country()
        year = int(input.ex_year())
        topn = int(input.ex_topn())
        df = df[(df["country"] == country) & (df["year"] == year)].copy()
        df = df.sort_values("streams_sum", ascending=False).head(topn)
        df["label"] = df["track_name"].astype(str).str.slice(0, 40)
        return df

    @output
    @render.ui
    def ex_kpis():
        _cys = cys()
        country = input.ex_country()
        year = int(input.ex_year())
        sel = _cys[(_cys["country"] == country) & (_cys["year"] == year)]
        if len(sel) != 1:
            return ui.div()
        r = sel.iloc[0]
        return ui.div(
            kpi_card("Total Streams", f"{r['total_streams']:,.0f}"),
            kpi_card("Unique Artists", f"{int(r['unique_artists']):,}"),
            kpi_card("Unique Tracks", f"{int(r['unique_tracks']):,}"),
            class_="kpi-row",
        )

    @output
    @render.ui
    def ex_bar():
        df = ex_df()
        country = input.ex_country()
        year = int(input.ex_year())
        if df.empty:
            return ui.div(ui.p("No rows for this selection.", class_="note"))
        fig = px.bar(
            df.sort_values("streams_sum"),
            x="streams_sum",
            y="label",
            orientation="h",
            hover_data={
                "track_name": True,
                "artist_name": True,
                "streams_sum": ":,.0f",
                "best_rank": True,
                "days_charted": True,
                "label": False,
            },
            title=f"Top Tracks — {country} ({year})",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=60, b=0), yaxis_title="", xaxis_title="Streams (sum)")
        return ui.div(ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)), class_="plotly")

    @output
    @render.ui
    def ex_table_expander():
        df = ex_df()
        if df.empty:
            return ui.div()
        # Simple "expander"-like section
        return ui.details(
            ui.summary("Show data table"),
            ui.output_data_frame("ex_table"),
        )

    @output
    @render.data_frame
    def ex_table():
        df = ex_df()
        cols = ["track_name", "artist_name", "streams_sum", "best_rank", "days_charted"]
        return render.DataGrid(df[cols], height="360px")

    # -------------------------
    # TRENDS
    # -------------------------
    @reactive.effect
    def _update_country_choices_for_artist():
        _ay = ay()
        artist = input.tr_artist()
        df_a = _ay[_ay["artist_name"] == artist]
        choices = sorted(df_a["country"].dropna().unique().tolist())
        selected = ["Global"] if "Global" in choices else []
        ui.update_selectize("tr_countries", choices=choices, selected=selected, session=session)

    @reactive.calc
    def tr_df_plot():
        _ay = ay()
        artist = input.tr_artist()
        df_a = _ay[_ay["artist_name"] == artist].copy()
        selected = list(input.tr_countries() or [])

        if selected:
            df_plot = df_a[df_a["country"].isin(selected)].copy()
        else:
            top5 = (
                df_a.groupby("country")["streams_sum"].sum().sort_values(ascending=False).head(5).index.tolist()
            )
            df_plot = df_a[df_a["country"].isin(top5)].copy()
        return df_plot.sort_values("year")

    @output
    @render.ui
    def tr_line():
        df = tr_df_plot()
        artist = input.tr_artist()
        if df.empty:
            return ui.div(ui.p("No trend rows for this artist.", class_="note"))
        fig = px.line(
            df,
            x="year",
            y="streams_sum",
            color="country",
            markers=True,
            title=f"{artist} — Streams Over Time",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=60, b=0), yaxis_title="Streams (sum)")
        return ui.div(ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)), class_="plotly")


# ✅ This is what fixes: "Attribute app not found"
app = App(app_ui, server)