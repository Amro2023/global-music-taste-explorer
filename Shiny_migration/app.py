# app.py — Shiny for Python (World View + Explorer + Trends) + Vibe Check globe
from __future__ import annotations

from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
import plotly.express as px
from spotify_api import search_spotify, enrich_rows_with_genre


from shiny import App, ui, render, reactive


# -------------------------
# Paths (robust)
# -------------------------
APP_DIR = Path(__file__).resolve().parent
EXPORTS = APP_DIR / "exports"
if not EXPORTS.exists():
    EXPORTS = APP_DIR.parent / "exports"


# -------------------------
# Data loading (cached)
# -------------------------
@lru_cache(maxsize=1)
def data():
    cys = pd.read_parquet(EXPORTS / "country_year_summary.parquet")
    tt = pd.read_parquet(EXPORTS / "top_tracks_country_year_top500.parquet")
    ay = pd.read_parquet(EXPORTS / "artist_country_year_top200.parquet")
    iso = pd.read_csv(EXPORTS / "country_iso3_map.csv")

    # Standardize column names
    cys.columns = cys.columns.str.strip().str.lower()
    tt.columns = tt.columns.str.strip().str.lower()
    ay.columns = ay.columns.str.strip().str.lower()
    iso.columns = iso.columns.str.strip().str.lower()

    # Normalize cys schema
    cys = cys.rename(columns={"region": "country"})

    if "total_streams" in cys.columns and "streams_sum" not in cys.columns:
        cys = cys.rename(columns={"total_streams": "streams_sum"})

    if "avg_streams" in cys.columns and "streams_avg" not in cys.columns:
        cys = cys.rename(columns={"avg_streams": "streams_avg"})

    # Add iso3 to cys from mapping file
    if "iso3" not in cys.columns:
        cys = cys.merge(
            iso[["country", "iso3"]].drop_duplicates(),
            on="country",
            how="left"
        )

    # Normalize tt schema to canonical names expected by the app
    tt = tt.rename(
        columns={
            "region": "country",
            "title": "track_name",
            "artist": "artist_name",
            "streams": "streams_sum",
        }
    )

    # Normalize ay schema
    ay = ay.rename(
        columns={
            "region": "country",
            "artist": "artist_name",
            "streams": "streams_sum",
        }
    )

    # Normalize dtypes
    if "year" in cys.columns:
        cys["year"] = pd.to_numeric(cys["year"], errors="coerce").astype("Int64")
    if "year" in tt.columns:
        tt["year"] = pd.to_numeric(tt["year"], errors="coerce").astype("Int64")
    if "year" in ay.columns:
        ay["year"] = pd.to_numeric(ay["year"], errors="coerce").astype("Int64")
    print("CYS final columns:", list(cys.columns))
    return cys, tt, ay


@lru_cache(maxsize=1)
def vibe_data():
    vibe_path = EXPORTS / "vibe_country_date.parquet"
    if not vibe_path.exists():
        return None
    vdf = pd.read_parquet(vibe_path)
    if "snapshot_date" in vdf.columns:
        vdf["snapshot_date"] = pd.to_datetime(vdf["snapshot_date"]).dt.date
    return vdf


def kpi_card(label: str, value: str):
    return ui.div(
        ui.div(label, class_="kpi-label"),
        ui.div(value, class_="kpi-value"),
        class_="kpi-card",
    )

# -------------------------
# Shared country list + Spotify market mapping
# -------------------------
country_year_summary, top_tracks, artist_year = data()

APP_COUNTRIES = sorted(
    top_tracks["country"].dropna().astype(str).unique().tolist()
)

COUNTRY_TO_SPOTIFY_MARKET = {
    "ARGENTINA": "AR",
    "AUSTRALIA": "AU",
    "AUSTRIA": "AT",
    "BELGIUM": "BE",
    "BOLIVIA": "BO",
    "BRAZIL": "BR",
    "BULGARIA": "BG",
    "CANADA": "CA",
    "CHILE": "CL",
    "COLOMBIA": "CO",
    "COSTA RICA": "CR",
    "CZECH REPUBLIC": "CZ",
    "DENMARK": "DK",
    "DOMINICAN REPUBLIC": "DO",
    "ECUADOR": "EC",
    "EGYPT": "EG",
    "EL SALVADOR": "SV",
    "ESTONIA": "EE",
    "FINLAND": "FI",
    "FRANCE": "FR",
    "GERMANY": "DE",
    "GREECE": "GR",
    "GUATEMALA": "GT",
    "HONDURAS": "HN",
    "HONG KONG": "HK",
    "HUNGARY": "HU",
    "ICELAND": "IS",
    "INDIA": "IN",
    "INDONESIA": "ID",
    "IRELAND": "IE",
    "ISRAEL": "IL",
    "ITALY": "IT",
    "JAPAN": "JP",
    "LATVIA": "LV",
    "LITHUANIA": "LT",
    "LUXEMBOURG": "LU",
    "MALAYSIA": "MY",
    "MEXICO": "MX",
    "MOROCCO": "MA",
    "NETHERLANDS": "NL",
    "NEW ZEALAND": "NZ",
    "NICARAGUA": "NI",
    "NORWAY": "NO",
    "PANAMA": "PA",
    "PARAGUAY": "PY",
    "PERU": "PE",
    "PHILIPPINES": "PH",
    "POLAND": "PL",
    "PORTUGAL": "PT",
    "ROMANIA": "RO",
    "RUSSIA": "RU",
    "SAUDI ARABIA": "SA",
    "SINGAPORE": "SG",
    "SLOVAKIA": "SK",
    "SOUTH AFRICA": "ZA",
    "SOUTH KOREA": "KR",
    "SPAIN": "ES",
    "SWEDEN": "SE",
    "SWITZERLAND": "CH",
    "TAIWAN": "TW",
    "THAILAND": "TH",
    "TURKEY": "TR",
    "UKRAINE": "UA",
    "UNITED ARAB EMIRATES": "AE",
    "UNITED KINGDOM": "GB",
    "UNITED STATES": "US",
    "URUGUAY": "UY",
    "VIETNAM": "VN",
    "Global": None,
}

BAD_TEXT_TERMS = {
    "top hits",
    "todays top hits",
    "today's top hits",
    "best top hits",
    "karaoke",
    "clean top hits playlist",
    "top hits today",
    "top hit music mix",
    "playlist",
    "radio edit",
}

COUNTRY_QUERY_MAP = {
    "UNITED STATES": "pop",
    "THAILAND": "thai pop",
    "UKRAINE": "ukrainian pop",
    "SAUDI ARABIA": "arab pop",
    "UNITED ARAB EMIRATES": "arab pop",
    "EGYPT": "arab pop",
    "MOROCCO": "moroccan pop",
    "ALGERIA": "rai",
    "INDIA": "bollywood",
    "PAKISTAN": "pakistani pop",
    "BRAZIL": "brazilian pop",
    "MEXICO": "latin pop",
    "COLOMBIA": "reggaeton",
    "NIGERIA": "afrobeats",
    "SOUTH AFRICA": "amapiano",
    "FRANCE": "french pop",
    "GERMANY": "german pop",
    "TURKEY": "turkish pop",
    "JAPAN": "j-pop",
    "KOREA, REPUBLIC OF": "k-pop",
}


def default_query_for_country(country: str) -> str:
    return COUNTRY_QUERY_MAP.get(str(country).upper(), "pop")


def looks_like_junk_result(row: dict) -> bool:
    text = " ".join([
        str(row.get("track_name", "")),
        str(row.get("artist_name", "")),
        str(row.get("album_name", "")),
    ]).lower()

    return any(term in text for term in BAD_TEXT_TERMS)


def clean_snapshot_rows(rows: list[dict]) -> list[dict]:
    cleaned = []
    seen = set()

    for row in rows:
        if looks_like_junk_result(row):
            continue

        key = (
            str(row.get("track_name", "")).strip().lower(),
            str(row.get("artist_name", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(row)

    return cleaned


def spotify_market_for_country(country_name: str):
    return COUNTRY_TO_SPOTIFY_MARKET.get(country_name)


def get_country_snapshot_rows(country, limit=10, genre=None):
    market = spotify_market_for_country(country)
    if market is None:
        return []

    query = (genre or "").strip() or default_query_for_country(country)

    try:
        rows = search_spotify(
            query,
            search_type="track",
            market=market,
            limit=10,
            genre=None,
        )


        rows = enrich_rows_with_genre(rows)
        rows = clean_snapshot_rows(rows)

        if genre and str(genre).strip():
            genre_lower = str(genre).strip().lower()
            rows = [
                r for r in rows
                if genre_lower in (r.get("genre") or "").lower()
                or genre_lower in str(r.get("track_name", "")).lower()
                or genre_lower in str(r.get("artist_name", "")).lower()
                or genre_lower in str(r.get("album_name", "")).lower()
            ]

        return rows[:limit]

    except Exception as e:
        print(f"Stable live snapshot search failed for country={country}, market={market}: {e}")
        return []



# -------------------------
# UI
# -------------------------
app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1")
    ),
    ui.tags.style(
        """
        /* ===============================
        GLOBAL TEXT
        =============================== */
        body {
        color: #e8e8e8;
        background-color: #111111;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .section-title {
        margin-top: 28px;
        margin-bottom: 16px;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1.2;
        }
        /* ===============================
        HEADERS
        =============================== */

        h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 800;
        }

        h4 {
        color: #ffffff !important;
        font-weight: 700;
        margin-top: 10px;
        }

        h5, h6 {
        color: #e6e6e6 !important;
        font-weight: 600;
        }

        /* ===============================
        GENERAL TEXT OUTPUT
        =============================== */

        .shiny-text-output,
        .shiny-html-output,
        p {
        color: #d8d8d8 !important;
        }

        /* ===============================
        TABLES
        =============================== */

        .table {
        color: #e8e8e8 !important;
        background-color: #181818 !important;
        border-radius: 8px;
        overflow: hidden;
        }

        .table th {
        color: #ffffff !important;
        background-color: #2a2a2a !important;
        font-weight: 700;
        border-bottom: 2px solid #3a3a3a;
        }

        .table td {
        color: #e6e6e6 !important;
        background-color: #181818 !important;
        }

        .table tr:nth-child(even) td {
        background-color: #1f1f1f !important;
        }

        /* ===============================
        KPI CARDS
        =============================== */

        .kpi-card {
        background: #1c1c1c;
        border-radius: 10px;
        padding: 14px 18px;
        min-width: 160px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }

        .kpi-label {
        font-size: 0.8rem;
        color: #9aa0a6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        }

        .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
        }

        /* ===============================
        BUTTONS
        =============================== */

        .btn-primary {
        background-color: #1db954 !important;
        border-color: #1db954 !important;
        }

        .btn-primary:hover {
        background-color: #1ed760 !important;
        }

        /* ===============================
        SIDEBAR INPUTS
        =============================== */

        .form-control,
        .form-select,
        .selectize-input,
        .selectize-control.single .selectize-input,
        .selectize-dropdown,
        .selectize-dropdown-content,
        .shiny-input-container input[type="text"] {
        background-color: #1a1a1a !important;
        color: #e6e6e6 !important;
        border: 1px solid #333 !important;
        }

        .selectize-input > input {
        color: #e6e6e6 !important;
        }

        .selectize-dropdown .option {
        background-color: #1a1a1a !important;
        color: #e6e6e6 !important;
        }

        .selectize-dropdown .active {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
        }     

        /* ===============================
        MOBILE / API PAGE READABILITY
        =============================== */

        .section-title {
        color: #ffffff !important;
        }

        .form-control,
        .form-select,
        .btn {
        width: 100%;
        max-width: 100%;
        }

        .btn,
        button {
        touch-action: manipulation;
        }

        .api-card {
        background: #171717;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 12px;
        }

        .api-card-label {
        color: #9aa0a6;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        }

        .api-card-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
        }

        @media (max-width: 768px) {
        .section-title {
            font-size: 1.2rem;
            line-height: 1.25;
        }

        .api-card-value {
            font-size: 1.3rem;
        }
        }  
        """
    ),

    ui.div(
        ui.h2("🎧 Global Music Taste Explorer (Shiny)", class_="gme-title"),
        ui.div("World View (Streams) + Vibe Check (daily Top 50 audio features).", class_="gme-sub"),
        class_="panel",
    ),

    ui.navset_tab(
        ui.nav_panel(
            "🌍 World View",
            ui.div(
                ui.div(
                    ui.p(
                        "Streams mode uses yearly Top 200 summaries. "
                        "Vibe Check mode uses daily Top 50 audio features. "
                        "Rotate the globe with the longitude slider.",
                        class_="note",
                    ),

                    # Map mode + conditional controls
                    ui.layout_columns(
                        ui.input_radio_buttons(
                            "wv_map_mode",
                            "Map Mode",
                            {"genre": "Streams", "vibe": "Vibe Check"},
                            selected="genre",
                        ),
                        ui.panel_conditional(
                            "input.wv_map_mode === 'genre'",
                            ui.input_slider("wv_year", "Year", min=2021, max=2021, value=2021, step=1),
                        ),
                        ui.panel_conditional(
                            "input.wv_map_mode === 'vibe'",
                            ui.input_select(
                                "wv_vibe_feature",
                                "Vibe Feature",
                                {
                                    "vibe_index": "Vibe Index",
                                    "energy_mean": "Energy",
                                    "danceability_mean": "Danceability",
                                    "valence_mean": "Valence (Happiness)",
                                    "acousticness_mean": "Acousticness",
                                },
                                selected="vibe_index",
                            ),
                        ),
                        col_widths=[4, 4, 4],
                    ),

                    ui.panel_conditional(
                        "input.wv_map_mode === 'genre'",
                        ui.layout_columns(
                            ui.input_switch("wv_log", "Log scale", value=True),
                            ui.input_numeric("wv_topn", "Top countries callout", value=10, min=3, max=25),
                            col_widths=[6, 6],
                        ),
                    ),

                    ui.panel_conditional(
                        "input.wv_map_mode === 'vibe'",
                        ui.layout_columns(
                            ui.input_date("wv_vibe_date", "Vibe Snapshot Date", value=None),
                            ui.input_numeric("wv_topn_vibe", "Top countries callout", value=10, min=3, max=25),
                            col_widths=[6, 6],
                        ),
                    ),

                    # Globe rotation controls (works for both)
                    ui.layout_columns(
                        ui.input_slider("wv_lon", "Rotate globe (longitude)", min=-180, max=180, value=0, step=1),
                        ui.input_slider("wv_lat", "Tilt globe (latitude)", min=-60, max=60, value=15, step=1),
                        col_widths=[6, 6],
                    ),

                    ui.output_ui("wv_kpis"),
                    ui.output_text("wv_snapshot_label"),
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
                        "Pick a country and year to explore top tracks. Keeping “Global” is useful as a benchmark.",
                        class_="note",
                    ),
                    ui.layout_columns(
                        ui.input_select("ex_country", "Country", choices=["Global"]),
                        ui.input_select("ex_year", "Year", choices=["2021"]),
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
            "Live Spotify Search",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_selectize(
                        "api_country",
                        "Market",
                        choices=APP_COUNTRIES,
                        selected="UNITED STATES",
                    ),
                    ui.input_text(
                        "api_genre",
                        "Search term or genre (optional)",
                        placeholder="e.g. pop, hip-hop, afrobeats",
                    ),
                    ui.input_action_button("api_go", "Load Search"),
                ),

                ui.div("Live Spotify Search Snapshot", class_="section-title"),
                ui.output_ui("api_snapshot_kpis"),

                ui.div(ui.output_text("api_status"), style="margin-bottom:10px; color:#9aa0a6;"),

                ui.div("Top Result", class_="section-title"),
                ui.output_ui("api_top_track_card"),

                ui.div("Top Track Results", class_="section-title"),
                ui.output_table("api_top_tracks"),

                ui.div("Top Artists in Results", class_="section-title"),
                ui.output_table("api_top_artists"),
            ),
        ),

        ui.nav_panel(
            "📈 Trends",
            ui.div(
                ui.div(
                    ui.p(
                        "Select an artist, then choose countries to compare. Tip: include “Global” as baseline.",
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

        

# -------------------------
# Server
# -------------------------
def server(input, output, session):
    @reactive.calc
    def cys():
        return data()[0]

    @reactive.calc
    def tt():
        return data()[1]

    @reactive.calc
    def ay():
        return data()[2]

    # Init choices once
    @reactive.effect
    def _init_choices():
        _cys = cys()
        _tt = tt()
        _ay = ay()

        years = sorted(pd.Series(_cys["year"]).dropna().unique().tolist())
        years = [int(y) for y in years if pd.notna(y)]
        if years:
            ui.update_slider("wv_year", min=min(years), max=max(years), value=max(years), session=session)
            ui.update_select("ex_year", choices=[str(y) for y in years], selected=str(max(years)), session=session)

        countries = sorted(pd.Series(_tt["country"]).dropna().unique().tolist())
        if countries:
            selected = "Global" if "Global" in countries else countries[0]

            # Explorer page country dropdown
            ui.update_select(
                "ex_country",
                choices=countries,
                selected=selected,
                session=session,
            )

            # Trends page country multiselect
            ui.update_selectize(
                "tr_countries",
                choices=countries,
                selected=["Global"] if "Global" in countries else [countries[0]],
                session=session,
            )

        top_artists = (
            _ay.groupby("artist_name")["streams_sum"].sum().sort_values(ascending=False).head(500).index.tolist()
            if ("artist_name" in _ay.columns and "streams_sum" in _ay.columns)
            else []
        )
        if top_artists:
            ui.update_select("tr_artist", choices=top_artists, selected=top_artists[0], session=session)

        # Default vibe date to latest
        vdf = vibe_data()
        if vdf is not None and "snapshot_date" in vdf.columns and len(vdf) > 0:
            latest = max(pd.Series(vdf["snapshot_date"]).dropna().unique().tolist())
            try:
                ui.update_date("wv_vibe_date", value=latest, session=session)
            except Exception:
                # If update_date isn't available in your Shiny version, UI default is still fine
                pass

    # API Snapshot Server Block
        @render.text
        @reactive.event(input.api_go)
        def api_status():
            country = input.api_country()
            genre = (input.api_genre() or "").strip()
            market = spotify_market_for_country(country)

            if market is None:
                return f"Spotify API does not support the '{country}' market."

            query_used = genre if genre else default_query_for_country(country)
            return f"Loaded live Spotify search for {country} ({market}) using '{query_used}'."




        @render.ui
        @reactive.event(input.api_go)
        def api_snapshot_kpis():
            country = input.api_country()
            genre = (input.api_genre() or "").strip()

            try:
                rows = get_country_snapshot_rows(country, limit=10, genre=genre if genre else None)

                if not rows:
                    return ui.div(
                        {"class": "alert alert-warning"},
                        f"No live Spotify snapshot data returned for {country}."
                    )

                df = pd.DataFrame(rows)

                track_col = "track_name" if "track_name" in df.columns else None
                artist_col = "artist_name" if "artist_name" in df.columns else None
                album_col = "album_name" if "album_name" in df.columns else None
                genre_col = "genre" if "genre" in df.columns else None

                top_track = df.iloc[0][track_col] if track_col and len(df) > 0 else "N/A"
                top_artist = df.iloc[0][artist_col] if artist_col and len(df) > 0 else "N/A"
                top_album = df.iloc[0][album_col] if album_col and len(df) > 0 else "N/A"
                top_genre = df.iloc[0][genre_col] if genre_col and pd.notna(df.iloc[0][genre_col]) else (genre if genre else "N/A")
                unique_artists = df[artist_col].nunique() if artist_col and artist_col in df.columns else 0

                return ui.div(
                    ui.div(
                        kpi_card("Country", country),
                        kpi_card("Top Track", str(top_track)),
                        kpi_card("Top Artist", str(top_artist)),
                        kpi_card("Top Album", str(top_album)),
                        kpi_card("Top Genre", str(top_genre)),
                        kpi_card("Artists in Top 10", str(unique_artists)),
                        style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:20px;",
                    )
                )

            except Exception as e:
                return ui.div(
                    {"class": "alert alert-danger"},
                    f"Live Spotify snapshot failed: {e}"
                )


        @render.ui
        @reactive.event(input.api_go)
        def api_top_track_card():
            country = input.api_country()
            genre = (input.api_genre() or "").strip()

            try:
                rows = get_country_snapshot_rows(country, limit=10, genre=genre if genre else None)

                if not rows:
                    return ui.div(
                        {"class": "alert alert-warning"},
                        f"No live top track returned for {country}."
                    )

                df = pd.DataFrame(rows)
                top = df.iloc[0]

                artwork = None
                if "album_image" in df.columns and pd.notna(top.get("album_image")) and top.get("album_image"):
                    artwork = ui.tags.img(
                        src=top["album_image"],
                        style="width:100%; max-width:260px; border-radius:14px; box-shadow:0 4px 14px rgba(0,0,0,0.18);"
                    )
                else:
                    artwork = ui.div(
                        ui.p("No artwork available."),
                        style="""
                            width:100%;
                            max-width:260px;
                            min-height:260px;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            border:1px solid #ddd;
                            border-radius:14px;
                            background:#f8f9fa;
                        """
                    )

                details = ui.div(
                    ui.h4(str(top.get("track_name", "N/A"))),
                    ui.p(f"Artist: {top.get('artist_name', 'N/A')}"),
                    ui.p(f"Album: {top.get('album_name', 'N/A')}"),
                    ui.p(f"Genre: {top.get('genre', 'N/A') or 'N/A'}"),
                    ui.a(
                        "Open in Spotify",
                        href=top.get("spotify_url"),
                        target="_blank",
                    ) if top.get("spotify_url") else ui.div(),
                )

                return ui.div(
                    ui.layout_columns(
                        ui.div(artwork),
                        ui.div(details),
                        col_widths=[4, 8],
                    ),
                    class_="panel",
                )

            except Exception as e:
                return ui.div(
                    {"class": "alert alert-danger"},
                    f"Unable to load album artwork card: {e}"
                )


        @render.table
        @reactive.event(input.api_go)
        def api_top_tracks():
            country = input.api_country()
            genre = (input.api_genre() or "").strip()

            try:
                rows = get_country_snapshot_rows(
                    country,
                    limit=10,
                    genre=genre if genre else None,
                )

                if not rows:
                    return pd.DataFrame([{"message": f"No live track data returned for {country}."}])

                df = pd.DataFrame(rows).copy()

                if df.empty:
                    return pd.DataFrame([{"message": f"No live track data returned for {country}."}])

                rename_map = {
                    "track_name": "Track",
                    "artist_name": "Artist",
                    "album_name": "Album",
                    "genre": "Genre",
                }

                df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

                keep_cols = [c for c in ["Track", "Artist", "Album", "Genre"] if c in df.columns]
                if keep_cols:
                    df = df[keep_cols]

                if "Genre" in df.columns:
                    df["Genre"] = df["Genre"].fillna("—").replace("", "—")

                return df.head(10).reset_index(drop=True)

            except Exception as e:
                return pd.DataFrame([{"error": str(e)}])



        @render.table
        @reactive.event(input.api_go)
        def api_top_artists():
            country = input.api_country()
            genre = (input.api_genre() or "").strip()

            try:
                rows = get_country_snapshot_rows(country, limit=20, genre=genre if genre else None)

                if not rows:
                    return pd.DataFrame([{"message": f"No live artist data returned for {country}."}])

                df = pd.DataFrame(rows).copy()

                if "artist_name" not in df.columns:
                    return pd.DataFrame([{"message": "Artist column not found in Spotify response."}])

                artist_df = (
                    df.assign(artist_name=df["artist_name"].fillna("Unknown"))
                    .groupby("artist_name", dropna=False)
                    .size()
                    .reset_index(name="Tracks in Results")
                    .sort_values("Tracks in Results", ascending=False)
                    .head(5)
                )

                return artist_df.rename(columns={"artist_name": "Artist"})

            except Exception as e:
                return pd.DataFrame([{"error": str(e)}])



    # -------------------------
    # WORLD VIEW: Streams map data
    # -------------------------
    @reactive.calc
    def wv_df_map():
        df = cys().copy()
        y = int(input.wv_year())
        df = df[(df["year"] == y) & (df["iso3"].notna()) & (df["country"] != "Global")].copy()

        # Handle both naming conventions just in case:
        streams_col = "streams_sum" if "streams_sum" in df.columns else ("total_streams" if "total_streams" in df.columns else None)
        if streams_col is None:
            return df.iloc[0:0].copy()

        df["streams_for_color"] = df[streams_col].clip(lower=1)
        df["color_val"] = df["streams_for_color"]
        if bool(input.wv_log()):
            df["color_val"] = np.log10(df["color_val"])
        return df

    # -------------------------
    # WORLD VIEW: Vibe map data
    # -------------------------
    @reactive.calc
    def wv_vibe_df_map():
        vdf = vibe_data()
        if vdf is None or vdf.empty:
            return pd.DataFrame(columns=["iso3", "country", "map_value", "n_tracks"])

        d = input.wv_vibe_date()
        if d is None:
            latest = max(pd.Series(vdf["snapshot_date"]).dropna().unique().tolist())
            d = latest

        feat = input.wv_vibe_feature()
        if feat is None or feat not in vdf.columns:
            return pd.DataFrame(columns=["iso3", "country", "map_value", "n_tracks"])
        
        # --- choose closest available snapshot date (<= selected) ---
        # make sure snapshot_date is datetime
        # --- choose closest available snapshot date (<= selected) robustly ---
        vdf = vdf.copy()
        vdf["snapshot_date"] = pd.to_datetime(vdf["snapshot_date"], errors="coerce")

        d = input.wv_vibe_date()
        d = pd.to_datetime(d, errors="coerce")

        available = (
            pd.Series(vdf["snapshot_date"].dropna().unique())
            .sort_values()
            .reset_index(drop=True)
        )

        if available.empty:
            return pd.DataFrame(columns=["iso3", "country", "map_value", "n_tracks"])

        # If the selected date is invalid/NaT, use latest
        if pd.isna(d):
            closest_date = available.iloc[-1]
        else:
            # index of rightmost date <= d
            idx = int(available.searchsorted(d, side="right") - 1)

            # if user picked earlier than earliest available date, use earliest (NOT latest)
            if idx < 0:
                idx = 0

            closest_date = available.iloc[idx]

        sub = vdf[vdf["snapshot_date"] == closest_date].copy()
        if sub.empty:
            return pd.DataFrame(columns=["iso3", "country", "map_value", "n_tracks"])
        
        sub["map_value"] = pd.to_numeric(sub[feat], errors="coerce")
        sub = sub.dropna(subset=["iso3", "map_value"])

        # ✅ prevent country_x / country_y
        sub = sub.drop(columns=["country"], errors="ignore")

        country_lu = (
            cys()[["iso3", "country"]]
            .dropna(subset=["iso3"])
            .drop_duplicates(subset=["iso3"])
        )

        out = sub.merge(country_lu, on="iso3", how="left")
        out = out[out["country"].notna() & (out["country"] != "Global")].copy()

        if "n_tracks" not in out.columns:
            out["n_tracks"] = 50

        out["snapshot_used"] = closest_date
        return out[["iso3", "country", "map_value", "n_tracks", "snapshot_used"]]

    @output
    @render.text
    def wv_snapshot_label():
        dfv = wv_vibe_df_map()
        if dfv is None or dfv.empty or "snapshot_used" not in dfv.columns:
            return ""

        selected = input.wv_vibe_date()
        used = pd.to_datetime(dfv["snapshot_used"].iloc[0]).date()

        # selected might be None or string/date
        if selected is None:
            return f"Spotify Vibe Snapshot: {used}"

        selected = pd.to_datetime(selected).date()
        if selected == used:
            return f"Spotify Vibe Snapshot: {used}"
        return f"Spotify Vibe Snapshot: {used} (selected {selected})"
    # KPIs
    @output
    @render.ui
    def wv_kpis():
        mode = input.wv_map_mode()

        if mode == "genre":
            df = wv_df_map()
            if df.empty:
                return ui.div(ui.p("No map rows for this year.", class_="note"))

            streams_col = "streams_sum" if "streams_sum" in df.columns else ("total_streams" if "total_streams" in df.columns else None)
            unique_art_col = "unique_artists" if "unique_artists" in df.columns else None

            total_streams = df[streams_col].sum() if streams_col else 0
            uniq_art_sum = df[unique_art_col].sum() if unique_art_col else 0

            return ui.div(
                kpi_card("Total Streams", f"{total_streams:,.0f}"),
                kpi_card("Countries", f"{df['country'].nunique():,}"),
                kpi_card("Unique Artists (sum)", f"{uniq_art_sum:,.0f}"),
                class_="kpi-row",
            )

        # Vibe KPIs
        dfv = wv_vibe_df_map()
        if dfv.empty:
            return ui.div(ui.p("No vibe rows for this date.", class_="note"))

        feat = input.wv_vibe_feature()
        feat_label = {
            "vibe_index": "Vibe Index",
            "energy_mean": "Energy",
            "danceability_mean": "Danceability",
            "valence_mean": "Valence",
            "acousticness_mean": "Acousticness",
        }.get(feat, str(feat))

        return ui.div(
            kpi_card("Countries", f"{dfv['iso3'].nunique():,}"),
            kpi_card(f"Avg {feat_label}", f"{dfv['map_value'].mean():.3f}"),
            kpi_card("Tracks Included (sum)", f"{int(dfv['n_tracks'].sum()):,}"),
            class_="kpi-row",
        )

    # Map (TRUE rotating globe)
    @output
    @render.ui
    def wv_map():
        mode = input.wv_map_mode()
        lon = int(input.wv_lon())
        lat = int(input.wv_lat())

        if mode == "genre":
            df = wv_df_map()
            y = int(input.wv_year())
            if df.empty:
                return ui.div(ui.p("No map data.", class_="note"))

            streams_col = "streams_sum" if "streams_sum" in df.columns else ("total_streams" if "total_streams" in df.columns else None)

            fig = px.choropleth(
                df,
                locations="iso3",
                color="color_val",
                hover_name="country",
                hover_data={
                    streams_col: ":,.0f" if streams_col else True,
                    "unique_tracks": ":," if "unique_tracks" in df.columns else True,
                    "unique_artists": ":," if "unique_artists" in df.columns else True,
                    "streams_avg": ":,.2f" if "streams_avg" in df.columns else True,
                    "chart_rows": ":," if "chart_rows" in df.columns else True,
                    "iso3": False,
                    "color_val": False,
                },
                color_continuous_scale="Viridis",
                title=f"Total Streams by Country — {y}",
            )

            # TRUE globe
            fig.update_geos(
                projection_type="orthographic",
                projection_rotation=dict(lon=lon, lat=lat),
                showframe=False,
                showcountries=True,
                countrycolor="rgba(0,0,0,0.25)",
                showcoastlines=True,
                coastlinecolor="rgba(0,0,0,0.18)",
                showocean=True,
                oceancolor="rgb(245,247,250)",
                showland=True,
                landcolor="rgb(235,238,242)",
                bgcolor="rgba(0,0,0,0)",
            )

            fig.update_layout(
                margin=dict(l=0, r=0, t=60, b=0),
                uirevision="stay",
                coloraxis_colorbar=dict(
                    title="Streams" if not bool(input.wv_log()) else "log10(Streams)",
                    tickformat="~s",
                    len=0.7,
                    thickness=14,
                ),
            )

            return ui.div(ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)), class_="plotly")

        # Vibe mode
        dfv = wv_vibe_df_map()
        if dfv.empty:
            return ui.div(ui.p("No vibe map data for this date.", class_="note"))

        feat = input.wv_vibe_feature()
        feat_label = {
            "vibe_index": "Vibe Index",
            "energy_mean": "Energy",
            "danceability_mean": "Danceability",
            "valence_mean": "Valence (Happiness)",
            "acousticness_mean": "Acousticness",
        }.get(feat, str(feat))

        d = input.wv_vibe_date()

        fig = px.choropleth(
            dfv,
            locations="iso3",
            color="map_value",
            hover_name="country",
            hover_data={"n_tracks": True, "map_value": ":.3f", "iso3": False},
            color_continuous_scale="Viridis",
            title=f"{feat_label} by Country — {d}",
        )

        fig.update_geos(
            projection_type="orthographic",
            projection_rotation=dict(lon=lon, lat=lat),
            showframe=False,
            showcountries=True,
            countrycolor="rgba(0,0,0,0.25)",
            showcoastlines=True,
            coastlinecolor="rgba(0,0,0,0.18)",
            showocean=True,
            oceancolor="rgb(245,247,250)",
            showland=True,
            landcolor="rgb(235,238,242)",
            bgcolor="rgba(0,0,0,0)",
        )

        fig.update_layout(
            margin=dict(l=0, r=0, t=60, b=0),
            uirevision="stay",
            coloraxis_colorbar=dict(
                title=feat_label,
                tickformat=".2f",
                len=0.7,
                thickness=14,
            ),
        )

        return ui.div(ui.HTML(fig.to_html(include_plotlyjs="cdn", full_html=False)), class_="plotly")

    @output
    @render.text
    def wv_table_title():
        mode = input.wv_map_mode()
        if mode == "genre":
            return f"Top {int(input.wv_topn())} Countries (by streams)"

        feat = input.wv_vibe_feature()
        feat_label = {
            "vibe_index": "Vibe Index",
            "energy_mean": "Energy",
            "danceability_mean": "Danceability",
            "valence_mean": "Valence",
            "acousticness_mean": "Acousticness",
        }.get(feat, str(feat))
        return f"Top {int(input.wv_topn_vibe())} Countries (by {feat_label})"

    @output
    @render.data_frame
    def wv_top_table():
        mode = input.wv_map_mode()

        if mode == "genre":
            df = wv_df_map()
            n = int(input.wv_topn())
            if df.empty:
                return render.DataGrid(pd.DataFrame(), height="320px")

            streams_col = "streams_sum" if "streams_sum" in df.columns else ("total_streams" if "total_streams" in df.columns else None)
            if streams_col is None:
                return render.DataGrid(pd.DataFrame(), height="320px")

            top_c = df.sort_values(streams_col, ascending=False).head(n)
            cols = ["country", streams_col]
            # add optional columns if present
            for c in ["unique_artists", "unique_tracks"]:
                if c in top_c.columns:
                    cols.append(c)
            return render.DataGrid(top_c[cols], height="320px")

        dfv = wv_vibe_df_map()
        n = int(input.wv_topn_vibe())
        if dfv.empty:
            return render.DataGrid(pd.DataFrame(), height="320px")

        top_v = dfv.sort_values("map_value", ascending=False).head(n)
        return render.DataGrid(top_v[["country", "map_value", "n_tracks", "iso3"]], height="320px")

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

        # handle naming
        streams_val = r["streams_sum"] if "streams_sum" in sel.columns else (r["total_streams"] if "total_streams" in sel.columns else 0)

        return ui.div(
            kpi_card("Total Streams", f"{streams_val:,.0f}"),
            kpi_card("Unique Artists", f"{int(r['unique_artists']):,}" if "unique_artists" in sel.columns else "—"),
            kpi_card("Unique Tracks", f"{int(r['unique_tracks']):,}" if "unique_tracks" in sel.columns else "—"),
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
                "days_on_chart": True if "days_on_chart" in df.columns else True,
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
        return ui.tags.details(
            ui.tags.summary("Show data table"),
            ui.output_data_frame("ex_table"),
        )

    @output
    @render.data_frame
    def ex_table():
        df = ex_df()
        cols = [c for c in ["track_name", "artist_name", "streams_sum", "best_rank", "days_on_chart"] if c in df.columns]
        return render.DataGrid(df[cols], height="360px")

    # -------------------------
    # TRENDS
    # -------------------------
    @output
    @render.ui
    def tr_line():
        _ay = ay().copy()
        artist = input.tr_artist()

        if artist is None or artist == "(loading...)":
            return ui.div(ui.p("Select an artist.", class_="note"))

        df = _ay[_ay["artist_name"] == artist].copy()
        if df.empty:
            return ui.div(ui.p("No rows for this artist.", class_="note"))

        countries = input.tr_countries()
        if countries:
            df = df[df["country"].isin(countries)].copy()
        else:
            # default top 5 countries by streams
            top5 = df.groupby("country")["streams_sum"].sum().sort_values(ascending=False).head(5).index.tolist()
            df = df[df["country"].isin(top5)].copy()

        df = df.sort_values("year")
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


app = App(app_ui, server)