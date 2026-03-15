🎵 Global Music Taste Explorer
Built with Shiny for Python
An interactive Shiny app that visualizes how music preferences evolve across countries and years using Spotify chart data.
Built with Python, Shiny for Python, Pandas, and Plotly.

🌍 Overview
Global Music Taste Explorer allows users to analyze music trends by selecting a country and year, with all visualizations updating dynamically through Shiny’s reactive framework.
The app explores:
Dominant genres by country-year
Top tracks and artists
Artist trends over time
Overall music diversity patterns

📊 Current Features
Country & Year Filters
Interactive selectors drive all outputs reactively.
Summary Panel
Displays key metrics for the selected country-year:
Total chart entries
Dominant genre
Artist diversity
Top Tracks Table
Top 500 tracks including rank, artist, and popularity.
Artist Trend Visualization
Plotly-based trend analysis using Top 200 artist data across years.

🗂️ Data Sources
Preprocessed parquet files stored in:
exports/
country_year_summary.parquet
top_tracks_country_year_top500.parquet
artist_country_year_top200.parquet
Data is aggregated by country and year for performance optimization.

🛠 Tech Stack
Python 3.11
Shiny for Python
Pandas
Plotly
Parquet
Run locally:
shiny run --reload app.py

🚀 Status
The app currently supports multi-country, multi-year analysis with fast reactive filtering and is structured for deployment to shinyapps.io.

# Global Music Taste Explorer

Interactive Shiny for Python application exploring global Spotify listening trends.

## Project Structure Data Pipeline

# Global Music Taste Explorer

Interactive Shiny for Python application exploring global Spotify listening trends.

## Project Structure
global-music-taste-explorer
│
├── Shiny_migration
│ ├── app.py
│ ├── exports
│ └── scripts

## Running the App

From the project root:
cd Shiny_migration
shiny run --reload app.py

The app will launch locally at:
http://127.0.0.1:8000

---

# Data Pipeline

The dataset powering the app is generated from the **Spotify Charts dataset via KaggleHub**.

To rebuild all export files:
python Shiny_migration/scripts/build_exports_spotify_charts.py

This script generates the following files inside:
Shiny_migration/exports/

- `country_year_summary.parquet`
- `top_tracks_country_year_top500.parquet`
- `artist_country_year_top200.parquet`
- `vibe_country_date.parquet`
- `country_iso3_map.csv`

These files power all visualizations in the app.

Exports are **gitignored** and must be rebuilt locally.

---

## Dataset Coverage

Current coverage:
2017
2018
2019
2020
2021

Future updates may integrate **Spotify API data for live updates**.




Made by Amro Osman, Sanjog Kadayat, Shiela Green, and Margarida Sacouto
