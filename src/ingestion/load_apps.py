import os
import sys
import time
from datetime import datetime

import requests
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "db"))
from connection import get_engine

STEAMSPY_TOP_URL = "https://steamspy.com/api.php?request=top100in2weeks"
STORE_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
REQUEST_DELAY_SECONDS = 1.5  # be polite to the unofficial store API
SEED_LIMIT = 50              # how many games to pull in for now


def get_seed_appids(limit=SEED_LIMIT):
    """Pull currently popular games from SteamSpy as our starting universe."""
    response = requests.get(STEAMSPY_TOP_URL, timeout=10)
    response.raise_for_status()
    data = response.json()  # dict keyed by appid (as string)
    return [int(appid) for appid in list(data.keys())[:limit]]


def fetch_app_details(appid):
    """Call Steam's storefront API for one app's metadata."""
    params = {"appids": appid, "cc": "us", "l": "en"}
    response = requests.get(STORE_APPDETAILS_URL, params=params, timeout=10)
    response.raise_for_status()
    entry = response.json().get(str(appid))
    if not entry or not entry.get("success"):
        return None
    return entry["data"]


def parse_release_date(details):
    raw = (details.get("release_date") or {}).get("date")
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%b %d, %Y").date()
    except ValueError:
        return None  # some entries say things like "Coming soon" instead of a real date


def get_or_create_genre(conn, genre_name):
    conn.execute(
        text("INSERT INTO genres (genre_name) VALUES (:name) ON CONFLICT (genre_name) DO NOTHING"),
        {"name": genre_name},
    )
    result = conn.execute(text("SELECT genre_id FROM genres WHERE genre_name = :name"), {"name": genre_name})
    return result.scalar()


def upsert_app(conn, appid, details):
    conn.execute(
        text("""
            INSERT INTO apps (appid, name, developer, publisher, release_date, is_free)
            VALUES (:appid, :name, :developer, :publisher, :release_date, :is_free)
            ON CONFLICT (appid) DO UPDATE SET
                name = EXCLUDED.name,
                developer = EXCLUDED.developer,
                publisher = EXCLUDED.publisher,
                release_date = EXCLUDED.release_date,
                is_free = EXCLUDED.is_free
        """),
        {
            "appid": appid,
            "name": details.get("name"),
            "developer": ", ".join(details.get("developers") or []),
            "publisher": ", ".join(details.get("publishers") or []),
            "release_date": parse_release_date(details),
            "is_free": details.get("is_free", False),
        },
    )
    for genre in details.get("genres") or []:
        genre_id = get_or_create_genre(conn, genre["description"])
        conn.execute(
            text("INSERT INTO app_genres (appid, genre_id) VALUES (:appid, :genre_id) ON CONFLICT DO NOTHING"),
            {"appid": appid, "genre_id": genre_id},
        )


def main():
    engine = get_engine()
    appids = get_seed_appids()
    print(f"Fetched {len(appids)} candidate appids from SteamSpy")

    for i, appid in enumerate(appids, start=1):
        print(f"[{i}/{len(appids)}] Fetching appid {appid}...")
        details = fetch_app_details(appid)
        if details is None:
            print("  -> skipped (no data or delisted)")
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        with engine.begin() as conn:
            upsert_app(conn, appid, details)
        print(f"  -> saved: {details.get('name')}")
        time.sleep(REQUEST_DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    main()