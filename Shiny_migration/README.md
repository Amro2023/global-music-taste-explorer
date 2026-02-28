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

Made by Amro Osman, Sanjog Kadayat, Shiela Green, and Margarida Sacouto
