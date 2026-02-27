from pathlib import Path
import pandas as pd
import kagglehub


REPO_ROOT = Path(__file__).resolve().parents[1]  # for scripts/ in repo root

# If you're in Shiny_migration/scripts, parents[2] is the repo root.
if REPO_ROOT.name == "Shiny_migration":
    REPO_ROOT = REPO_ROOT.parent

EXPORTS = REPO_ROOT / "exports"
EXPORTS.mkdir(exist_ok=True)

# --- Download Kaggle dataset ---
path = Path(kagglehub.dataset_download("dhruvildave/spotify-charts"))
csv_path = path / "charts.csv"

print("Dataset folder:", path)
print("Reading:", csv_path)

df = pd.read_csv(csv_path)

# --- Basic cleanup ---
# Expected columns include: title, rank, date, artist, url, region, chart, trend, streams
# (Exact set can vary slightly, but these are the important ones.)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "region", "chart", "rank"])

# --- Filter to 2021 and Top 200 chart only ---
df_2021 = df[(df["date"].dt.year == 2021) & (df["chart"].astype(str).str.lower() == "top200")].copy()

# Keep rank numeric + streams numeric
df_2021["rank"] = pd.to_numeric(df_2021["rank"], errors="coerce")
df_2021["streams"] = pd.to_numeric(df_2021.get("streams", None), errors="coerce")
df_2021 = df_2021.dropna(subset=["rank"]).copy()
df_2021["rank"] = df_2021["rank"].astype(int)

# Standardize region naming
df_2021["region"] = df_2021["region"].astype(str)

# Add year
df_2021["year"] = 2021

# ----------------------------
# Build exports for 2021
# ----------------------------

# 1) country_year_summary.parquet
# Simple, robust aggregation (you can add more stats later)
cys_2021 = (
    df_2021.groupby(["region", "year"], as_index=False)
    .agg(
        chart_rows=("rank", "size"),
        unique_tracks=("url", "nunique"),
        unique_artists=("artist", "nunique"),
        total_streams=("streams", "sum"),
        avg_streams=("streams", "mean"),
    )
)

# 2) top_tracks_country_year_top500.parquet
# Create a track id; url is best (Spotify track URL)
# Sum streams across the year by region + track, then take top 500
track_key = "url" if "url" in df_2021.columns else "title"
tt_2021 = (
    df_2021.groupby(["region", "year", track_key, "title", "artist"], as_index=False)
    .agg(
        streams=("streams", "sum"),
        best_rank=("rank", "min"),
        days_on_chart=("date", "nunique"),
    )
)

tt_2021 = tt_2021.sort_values(["region", "year", "streams"], ascending=[True, True, False])
tt_2021["rank_year"] = tt_2021.groupby(["region", "year"]).cumcount() + 1
tt_2021 = tt_2021[tt_2021["rank_year"] <= 500].copy()

# 3) artist_country_year_top200.parquet
ay_2021 = (
    df_2021.groupby(["region", "year", "artist"], as_index=False)
    .agg(
        streams=("streams", "sum"),
        track_count=(track_key, "nunique"),
        days_on_chart=("date", "nunique"),
        best_rank=("rank", "min"),
    )
)

ay_2021 = ay_2021.sort_values(["region", "year", "streams"], ascending=[True, True, False])
ay_2021["rank_year"] = ay_2021.groupby(["region", "year"]).cumcount() + 1
ay_2021 = ay_2021[ay_2021["rank_year"] <= 200].copy()

# ----------------------------
# Append into existing exports (dedupe)
# ----------------------------

def append_dedupe(existing_path: Path, new_df: pd.DataFrame, subset_keys: list[str]) -> None:
    if existing_path.exists():
        old = pd.read_parquet(existing_path)
        combined = pd.concat([old, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=subset_keys, keep="last")
    else:
        combined = new_df.copy()

    combined.to_parquet(existing_path, index=False)
    print("Wrote:", existing_path, "rows:", len(combined))

append_dedupe(
    EXPORTS / "country_year_summary.parquet",
    cys_2021,
    subset_keys=["region", "year"],
)

append_dedupe(
    EXPORTS / "top_tracks_country_year_top500.parquet",
    tt_2021,
    subset_keys=["region", "year", track_key],
)

append_dedupe(
    EXPORTS / "artist_country_year_top200.parquet",
    ay_2021,
    subset_keys=["region", "year", "artist"],
)

print("✅ Backfill complete. Commit the updated exports/ parquet files to GitHub.")