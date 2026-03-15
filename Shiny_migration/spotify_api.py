from pathlib import Path
import os
import base64
import requests
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise ValueError("Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in .env")

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"


def get_access_token() -> str:
    raw = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def spotify_get(url: str, params: dict | None = None) -> dict:
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def format_track_item(item: dict, genre: str | None = None) -> dict:
    album = item.get("album", {})
    images = album.get("images", [])

    album_image = images[0].get("url") if images else None
    artist_names = ", ".join(a.get("name", "") for a in item.get("artists", []))
    artist_ids = [a.get("id") for a in item.get("artists", []) if a.get("id")]

    return {
        "track_name": item.get("name"),
        "artist_name": artist_names,
        "artist_ids": artist_ids,
        "album_name": album.get("name"),
        "album_image": album_image,
        "spotify_url": item.get("external_urls", {}).get("spotify"),
        "genre": genre,
    }


def search_spotify(query, search_type="track", market="US", limit=10, genre=None):
    try:
        limit = int(limit)
    except Exception:
        limit = 10

    limit = max(1, min(limit, 10))

    params = {
        "q": str(query).strip(),
        "type": search_type,
        "market": market,
        "limit": limit,
    }

    data = spotify_get(SEARCH_URL, params=params)

    key_map = {
        "track": "tracks",
        "artist": "artists",
        "playlist": "playlists",
        "album": "albums",
    }

    bucket = key_map[search_type]
    items = data.get(bucket, {}).get("items", [])
    rows = []

    if search_type == "track":
        for item in items:
            rows.append(format_track_item(item, genre=genre))

    elif search_type == "artist":
        for item in items:
            rows.append(
                {
                    "name": item.get("name"),
                    "genres": ", ".join(item.get("genres", [])),
                    "followers": item.get("followers", {}).get("total"),
                    "spotify_url": item.get("external_urls", {}).get("spotify"),
                    "artist_id": item.get("id"),
                }
            )

    elif search_type == "playlist":
        for item in items:
            rows.append(
                {
                    "name": item.get("name"),
                    "owner": item.get("owner", {}).get("display_name"),
                    "playlist_id": item.get("id"),
                    "description": item.get("description"),
                    "tracks_total": item.get("tracks", {}).get("total"),
                    "spotify_url": item.get("external_urls", {}).get("spotify"),
                }
            )

    elif search_type == "album":
        for item in items:
            rows.append(
                {
                    "name": item.get("name"),
                    "artist": ", ".join(a["name"] for a in item.get("artists", [])),
                    "release_date": item.get("release_date"),
                    "total_tracks": item.get("total_tracks"),
                    "spotify_url": item.get("external_urls", {}).get("spotify"),
                }
            )

    return rows


def get_artist_genres(artist_id: str) -> list[str]:
    if not artist_id:
        return []

    try:
        data = spotify_get(f"https://api.spotify.com/v1/artists/{artist_id}")
        return data.get("genres", []) or []
    except Exception:
        return []


def enrich_rows_with_genre(rows: list[dict]) -> list[dict]:
    enriched = []

    for row in rows:
        artist_ids = row.get("artist_ids") or []
        primary_artist_id = artist_ids[0] if artist_ids else None
        genres = get_artist_genres(primary_artist_id)
        row["genre"] = ", ".join(genres[:3]) if genres else None
        enriched.append(row)

    return enriched
