import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "db"))
from connection import get_engine

st.set_page_config(page_title="Steam Market Pulse", layout="wide")

st.title("🎮 Steam Market Pulse")
st.caption(
    "A market-health dashboard built on live Steam data — ownership, "
    "engagement, and pricing trends across 50 tracked titles."
)

engine = get_engine()

# --- Overview metrics ---
overview = pd.read_sql("""
    SELECT
        (SELECT COUNT(*) FROM apps) AS total_games,
        (SELECT COUNT(*) FROM player_snapshots) AS total_snapshots,
        (SELECT MAX(captured_at) FROM player_snapshots) AS last_updated
""", engine).iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Games Tracked", int(overview["total_games"]))
col2.metric("Snapshots Collected", int(overview["total_snapshots"]))
col3.metric("Last Updated", str(overview["last_updated"]))

# --- Most owned games ---
st.header("Most Owned Games")

owned_df = pd.read_sql("""
    SELECT a.name,
           ROUND((o.owners_low + o.owners_high) / 2.0) AS owners_estimate
    FROM ownership_stats o
    JOIN apps a ON a.appid = o.appid
    ORDER BY owners_estimate DESC
    LIMIT 15
""", engine)

fig = px.bar(
    owned_df, x="owners_estimate", y="name", orientation="h",
    labels={"owners_estimate": "Estimated Owners", "name": ""},
)
fig.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

# --- Engagement by genre ---
st.header("Engagement by Genre (Concurrent Players)")
st.caption(
    "SteamSpy's playtime data was found unusable for every tracked game (a 2018 "
    "Steam privacy change broke third-party playtime sampling site-wide) - "
    "concurrent players are used here as a more reliable engagement proxy. "
    "Genres with fewer than 3 tracked games are excluded to avoid single-game skew."
)

genre_df = pd.read_sql("""
    SELECT g.genre_name,
           COUNT(DISTINCT a.appid) AS games_in_genre,
           ROUND(AVG(p.concurrent_players)) AS avg_concurrent_players
    FROM player_snapshots p
    JOIN apps a ON a.appid = p.appid
    JOIN app_genres ag ON ag.appid = a.appid
    JOIN genres g ON g.genre_id = ag.genre_id
    GROUP BY g.genre_name
    HAVING COUNT(DISTINCT a.appid) >= 3
    ORDER BY avg_concurrent_players DESC
""", engine)

fig_genre = px.bar(
    genre_df, x="avg_concurrent_players", y="genre_name", orientation="h",
    labels={"avg_concurrent_players": "Avg Concurrent Players", "genre_name": ""},
    hover_data=["games_in_genre"],
)
fig_genre.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_genre, use_container_width=True)

# --- Per-game time series ---
st.header("Player Count Over Time")

game_list = pd.read_sql("SELECT appid, name FROM apps ORDER BY name", engine)
selected_name = st.selectbox("Choose a game", game_list["name"])
selected_appid = int(game_list.loc[game_list["name"] == selected_name, "appid"].iloc[0])

timeseries_query = text("""
    SELECT captured_at, concurrent_players
    FROM player_snapshots
    WHERE appid = :appid
    ORDER BY captured_at
""")
timeseries_df = pd.read_sql(timeseries_query, engine, params={"appid": selected_appid})

if timeseries_df.empty:
    st.info("No snapshots collected yet for this game.")
else:
    fig_ts = px.line(
        timeseries_df, x="captured_at", y="concurrent_players",
        labels={"captured_at": "Time", "concurrent_players": "Concurrent Players"},
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    # --- Price trend for the same selected game ---
st.subheader(f"Price History: {selected_name}")

st.caption(
    "Price history begins from this project's data collection start date - "
    "Steam's API only exposes current pricing, not historical records, so "
    "this chart deepens the longer the automated collection runs."
)
price_ts_query = text("""
    SELECT captured_at, price_usd, discount_pct
    FROM price_snapshots
    WHERE appid = :appid
    ORDER BY captured_at
""")
price_ts_df = pd.read_sql(price_ts_query, engine, params={"appid": selected_appid})

if price_ts_df.empty:
    st.info("No price snapshots collected yet for this game.")
else:
    fig_price = px.line(
        price_ts_df, x="captured_at", y="price_usd",
        labels={"captured_at": "Time", "price_usd": "Price (USD)"},
    )
    st.plotly_chart(fig_price, use_container_width=True)

# --- Current deals (biggest active discounts across all tracked games) ---
st.header("Current Deals")
st.caption("Latest known price/discount per game, sorted by biggest active discount.")

deals_query = text("""
    WITH latest_prices AS (
        SELECT DISTINCT ON (a.appid) a.appid, a.name, ps.price_usd, ps.discount_pct, ps.captured_at
        FROM price_snapshots ps
        JOIN apps a ON a.appid = ps.appid
        ORDER BY a.appid, ps.captured_at DESC
    )
    SELECT name, price_usd, discount_pct
    FROM latest_prices
    WHERE discount_pct > 0
    ORDER BY discount_pct DESC
    LIMIT 10
""")
deals_df = pd.read_sql(deals_query, engine)

if deals_df.empty:
    st.info("No active discounts among tracked games right now.")
else:
    fig_deals = px.bar(
        deals_df, x="discount_pct", y="name", orientation="h",
        labels={"discount_pct": "Discount %", "name": ""},
        hover_data=["price_usd"],
    )
    fig_deals.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_deals, use_container_width=True)

# --- Achievement completion rates ---
st.header("Achievement Completion Rates")
st.caption(
    "Games with fewer than 5 tracked achievements are excluded to avoid "
    "small-sample skew (see sql/analysis/achievement_completion_rates.sql)."
)

achievement_query = text("""
    SELECT a.name,
           COUNT(*) AS achievements_tracked,
           ROUND(AVG(ac.global_completion_pct), 1) AS avg_completion_pct
    FROM achievement_stats ac
    JOIN apps a ON a.appid = ac.appid
    GROUP BY a.name
    HAVING COUNT(*) >= 5
    ORDER BY avg_completion_pct ASC
    LIMIT 10
""")
achievement_df = pd.read_sql(achievement_query, engine)

fig_achieve = px.bar(
    achievement_df, x="avg_completion_pct", y="name", orientation="h",
    labels={"avg_completion_pct": "Avg Completion %", "name": ""},
    hover_data=["achievements_tracked"],
)
fig_achieve.update_layout(yaxis={"categoryorder": "total descending"})
st.plotly_chart(fig_achieve, use_container_width=True)