import os
import sys
import time

import requests
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "db"))
from connection import get_engine

load_dotenv()

STEAM_API_KEY = os.getenv("STEAM_API_KEY")
CURRENT_PLAYERS_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
STORE_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
REQUEST_DELAY_SECONDS = 1.5


def get_tracked_appids(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT appid FROM apps ORDER BY appid"))
        return [row[0] for row in result]


def fetch_current_players(appid):
    params = {"appid": appid, "key": STEAM_API_KEY}
    try:
        response = requests.get(CURRENT_PLAYERS_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  -> warning: player count request failed for {appid}: {e}")
        return None
    data = response.json().get("response", {})
    if data.get("result") != 1:
        return None
    return data.get("player_count")


def fetch_price_info(appid):
    params = {"appids": appid, "cc": "us", "l": "en"}
    try:
        response = requests.get(STORE_APPDETAILS_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  -> warning: price request failed for {appid}: {e}")
        return None, None
    entry = response.json().get(str(appid))
    if not entry or not entry.get("success"):
        return None, None
    details = entry["data"]
    if details.get("is_free"):
        return 0.0, 0
    price_overview = details.get("price_overview")
    if not price_overview:
        return None, None
    price_usd = price_overview["final"] / 100
    discount_pct = price_overview.get("discount_percent", 0)
    return price_usd, discount_pct

def main():
    engine = get_engine()
    appids = get_tracked_appids(engine)
    print(f"Collecting snapshots for {len(appids)} tracked apps...")

    for i, appid in enumerate(appids, start=1):
        player_count = fetch_current_players(appid)
        time.sleep(REQUEST_DELAY_SECONDS)
        price_usd, discount_pct = fetch_price_info(appid)
        time.sleep(REQUEST_DELAY_SECONDS)

        with engine.begin() as conn:
            if player_count is not None:
                conn.execute(
                    text("INSERT INTO player_snapshots (appid, concurrent_players) VALUES (:appid, :count)"),
                    {"appid": appid, "count": player_count},
                )
            if price_usd is not None:
                conn.execute(
                    text("INSERT INTO price_snapshots (appid, price_usd, discount_pct) VALUES (:appid, :price, :discount)"),
                    {"appid": appid, "price": price_usd, "discount": discount_pct},
                )

        print(f"[{i}/{len(appids)}] appid {appid}: players={player_count}, price=${price_usd}, discount={discount_pct}%")

    print("Done.")


if __name__ == "__main__":
    main()