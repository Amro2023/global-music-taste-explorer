# app.py (Upgraded visuals + "premium" map + cleaner charts)
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Global Music Taste Explorer", layout="wide")

# --- Paths: works in Colab AND later in Streamlit Cloud (repo) ---
EXPORTS = Path("exports")
if not EXPORTS.exists():
    EXPORTS = Path("/content/global_music_explorer/exports")

@st.cache_data
def load_data():
    cys = pd.read_parquet(EXPORTS / "country_year_summary.parquet")
    tt = pd.read_parquet(EXPORTS / "top_tracks_country_year_top500.parquet")
    ay = pd.read_parquet(EXPORTS / "artist_country_year_top200.parquet")
    return cys, tt, ay

country_year_summary, top_tracks, artist_year = load_data()

# Precompute helper lists for speed + consistency
ALL_YEARS = sorted(country_year_summary["year"].dropna().unique())
MIN_YEAR, MAX_YEAR = int(min(ALL_YEARS)), int(max(ALL_YEARS))
DEFAULT_YEAR = MAX_YEAR

top_tracks["year"] = top_tracks["year"].astype(int)
artist_year["year"] = artist_year["year"].astype(int)
country_year_summary["year"] = country_year_summary["year"].astype(int)

# --- Light styling ---
st.markdown("""
<style>
.block-container {padding-top: 1.2rem;}
.small-note {opacity: 0.7; font-size: 0.92rem; margin-bottom: 0.75rem;}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🎧 Global Music Taste Explorer")
page = st.sidebar.radio("Pages", ["🌍 World View", "📊 Explorer", "📈 Trends"])

# Helpers
def kpi_row(items):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)

def apply_common_layout(fig):
    fig.update_layout(
        template="plotly_white",
        title_x=0.01,
        legend_title_text="",
        margin=dict(l=0, r=0, t=60, b=0),
    )
    return fig

# =========================================================
# 🌍 WORLD VIEW
# =========================================================
if page == "🌍 World View":
    st.title("🌍 World View")
    st.markdown(
        '<div class="small-note">Choropleth shows Spotify Top 200 performance by country for the selected year. “Global” is excluded from the map.</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns([2, 1.25, 1, 1])
    with c1:
        selected_year = st.slider("Year", MIN_YEAR, MAX_YEAR, DEFAULT_YEAR)
    with c2:
        metric = st.selectbox(
            "Map metric",
            ["Total Streams", "Unique Artists", "Unique Tracks", "Average Rank (lower is better)"],
            index=0
        )
    with c3:
        use_log = st.toggle("Log scale", value=True)
    with c4:
        show_top = st.number_input("Top countries callout", min_value=3, max_value=25, value=10)

    df_map = country_year_summary[
        (country_year_summary["year"] == selected_year) &
        (country_year_summary["iso3"].notna()) &
        (country_year_summary["country"] != "Global")
    ].copy()

    # KPI tiles
    kpi_row([
        ("Total Streams", f"{df_map['total_streams'].sum():,.0f}"),
        ("Countries", f"{df_map['country'].nunique():,}"),
        ("Unique Artists (sum)", f"{df_map['unique_artists'].sum():,.0f}"),
        ("Unique Tracks (sum)", f"{df_map['unique_tracks'].sum():,.0f}"),
    ])

    # Choose metric
    if metric == "Total Streams":
        df_map["metric_val"] = df_map["total_streams"].clip(lower=1)
        color_title = "Total Streams"
        allow_log = True
    elif metric == "Unique Artists":
        df_map["metric_val"] = df_map["unique_artists"].clip(lower=1)
        color_title = "Unique Artists"
        allow_log = True
    elif metric == "Unique Tracks":
        df_map["metric_val"] = df_map["unique_tracks"].clip(lower=1)
        color_title = "Unique Tracks"
        allow_log = True
    else:
        # Lower avg_rank is better → invert so “better” = higher
        df_map["metric_val"] = (1 / df_map["avg_rank"].replace(0, pd.NA)).astype(float)
        color_title = "Rank Quality (higher is better)"
        allow_log = False

    # log scaling for skewed metrics
    if use_log and allow_log:
        import numpy as np
        df_map["color_val"] = np.log10(df_map["metric_val"])
        legend = f"log10({color_title})"
    else:
        df_map["color_val"] = df_map["metric_val"]
        legend = color_title

    fig = px.choropleth(
        df_map,
        locations="iso3",
        color="color_val",
        hover_name="country",
        hover_data={
            "total_streams": ":,.0f",
            "unique_tracks": ":,d",
            "unique_artists": ":,d",
            "avg_rank": ":.2f",
            "iso3": False,
            "metric_val": False,
            "color_val": False
        },
        color_continuous_scale="Viridis",
        labels={"color_val": legend},
        title=f"{color_title} by Country — {selected_year}"
    )

    # Premium map feel
    fig.update_geos(
        showcoastlines=False,
        showframe=False,
        projection_type="natural earth",
        bgcolor="rgba(0,0,0,0)"
    )
    fig.update_layout(
        template="plotly_white",
        title_x=0.01,
        margin=dict(l=0, r=0, t=60, b=0),
        coloraxis_colorbar=dict(
            title=legend,
            ticks="outside",
            len=0.75
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # Story highlight
    if not df_map.empty and "total_streams" in df_map.columns:
        top1 = df_map.sort_values("total_streams", ascending=False).iloc[0]
        st.info(f"**{selected_year} highlight:** {top1['country']} led with **{top1['total_streams']:,.0f}** total streams.")

    st.subheader(f"Top {int(show_top)} Countries")
    if metric == "Average Rank (lower is better)":
        top_c = df_map.sort_values("avg_rank", ascending=True).head(int(show_top))
        st.dataframe(top_c[["country","avg_rank","total_streams","unique_artists","unique_tracks"]], use_container_width=True)
    else:
        top_c = df_map.sort_values("metric_val", ascending=False).head(int(show_top))
        st.dataframe(top_c[["country","metric_val","total_streams","unique_artists","unique_tracks"]], use_container_width=True)

# =========================================================
# 📊 EXPLORER
# =========================================================
elif page == "📊 Explorer":
    st.title("📊 Explorer")
    st.markdown(
        '<div class="small-note">Pick a country and year to explore top songs or top artists. Keeping “Global” here is useful as a worldwide benchmark.</div>',
        unsafe_allow_html=True
    )

    countries = sorted(top_tracks["country"].dropna().unique())
    years = sorted(top_tracks["year"].dropna().unique())

    left, right = st.columns([2, 1])
    with left:
        selected_country = st.selectbox(
            "Country",
            countries,
            index=countries.index("Global") if "Global" in countries else 0
        )
    with right:
        selected_year = st.selectbox("Year", years, index=len(years)-1 if years else 0)

    mode = st.radio("View", ["Top Songs", "Top Artists"], horizontal=True)
    top_n = st.slider("Top N", 10, 100, 25, step=5)

    # KPI row for selection (uses country_year_summary if available)
    cys_sel = country_year_summary[
        (country_year_summary["country"] == selected_country) &
        (country_year_summary["year"] == selected_year)
    ]
    if len(cys_sel) == 1:
        r = cys_sel.iloc[0]
        kpi_row([
            ("Total Streams", f"{r['total_streams']:,.0f}"),
            ("Unique Artists", f"{int(r['unique_artists']):,}"),
            ("Unique Tracks", f"{int(r['unique_tracks']):,}")
        ])

    if mode == "Top Songs":
        df = top_tracks[
            (top_tracks["country"] == selected_country) &
            (top_tracks["year"] == selected_year)
        ].copy()
        df = df.sort_values("streams_sum", ascending=False).head(top_n)

        df["label"] = df["track_name"].astype(str).str.slice(0, 45)

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
                "label": False
            },
            title=f"Top Songs — {selected_country} ({selected_year})"
        )
        fig.update_xaxes(tickformat="~s")  # 10M/100M formatting
        fig = apply_common_layout(fig)
        fig.update_layout(yaxis_title="", xaxis_title="Streams (sum)")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Show data table"):
            st.dataframe(df[["track_name","artist_name","streams_sum","best_rank","days_charted"]], use_container_width=True)

    else:
        df = top_tracks[
            (top_tracks["country"] == selected_country) &
            (top_tracks["year"] == selected_year)
        ].copy()

        df_art = (df.groupby("artist_name", as_index=False)
                    .agg(streams_sum=("streams_sum","sum"),
                         best_rank=("best_rank","min"),
                         tracks_in_top=("track_name","nunique"))
                    .sort_values("streams_sum", ascending=False)
                    .head(top_n))

        fig = px.bar(
            df_art.sort_values("streams_sum"),
            x="streams_sum",
            y="artist_name",
            orientation="h",
            hover_data={
                "streams_sum": ":,.0f",
                "best_rank": True,
                "tracks_in_top": True
            },
            title=f"Top Artists — {selected_country} ({selected_year})"
        )
        fig.update_xaxes(tickformat="~s")
        fig = apply_common_layout(fig)
        fig.update_layout(yaxis_title="", xaxis_title="Streams (sum)")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Show data table"):
            st.dataframe(df_art, use_container_width=True)

# =========================================================
# 📈 TRENDS
# =========================================================
elif page == "📈 Trends":
    st.title("📈 Trends")
    st.markdown(
        '<div class="small-note">Select an artist, then choose countries to compare. Tip: include “Global” as a baseline.</div>',
        unsafe_allow_html=True
    )

    top_artists = (artist_year.groupby("artist_name")["streams_sum"]
                   .sum().sort_values(ascending=False).head(500).index.tolist())

    selected_artist = st.selectbox("Artist (Top 500 global)", top_artists)

    df_a = artist_year[artist_year["artist_name"] == selected_artist].copy()
    all_countries = sorted(df_a["country"].dropna().unique())

    default_countries = ["Global"] if "Global" in all_countries else []
    selected_countries = st.multiselect("Countries", all_countries, default=default_countries)

    force_global = st.toggle("Always include Global baseline", value=("Global" in all_countries))
    if force_global and "Global" in all_countries and "Global" not in selected_countries:
        selected_countries = ["Global"] + selected_countries

    if selected_countries:
        df_plot = df_a[df_a["country"].isin(selected_countries)].copy()
    else:
        top5 = (df_a.groupby("country")["streams_sum"]
                .sum().sort_values(ascending=False).head(5).index.tolist())
        df_plot = df_a[df_a["country"].isin(top5)]

    fig = px.line(
        df_plot.sort_values("year"),
        x="year",
        y="streams_sum",
        color="country",
        markers=True,
        title=f"{selected_artist} — Streams Over Time"
    )
    fig = apply_common_layout(fig)
    fig.update_layout(yaxis_title="Streams (sum)")

    # Cleaner hover
    fig.update_traces(
        hovertemplate="%{x}<br>%{y:,.0f} streams<extra>%{fullData.name}</extra>"
    )

    st.plotly_chart(fig, use_container_width=True)
