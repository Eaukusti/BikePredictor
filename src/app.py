"""
Helsinki City Bike Availability — live status + short-term outlook.
Run locally with: streamlit run app.py
"""
import pandas as pd
import streamlit as st

from src.digitransit_client import fetch_stations

st.set_page_config(page_title="Helsinki City Bikes", page_icon="🚲", layout="centered")
st.title("🚲 Helsinki City Bike Availability")

# --- Live status, fetched fresh on every load ---
stations = fetch_stations()
df = pd.DataFrame(stations)

station_name = st.selectbox("Pick a station", sorted(df["name"].unique()))
row = df[df["name"] == station_name].iloc[0]

col1, col2 = st.columns(2)
col1.metric("Bikes available now", int(row["bikes_available"]))
col2.metric("Free docks now", int(row["docks_available"]))

# --- Recent trend, built from the history the GitHub Action accumulates ---
st.subheader("Recent trend")
try:
    hist = pd.read_csv("data/history.csv", parse_dates=["timestamp"])
    station_hist = hist[hist["name"] == station_name].tail(48)  # last ~12h at 15-min polling
    if station_hist.empty:
        st.info("No history for this station yet.")
    else:
        st.line_chart(station_hist.set_index("timestamp")["bikes_available"])
except FileNotFoundError:
    st.info("No history yet — the GitHub Action needs to run a few times first.")

# --- TODO: this is the "enrichment" step to build out yourself ---
# Ideas, roughly in order of effort:
#   1. Naive: average of the last N snapshots as a "right now" smoothing.
#   2. Better: average availability at this same hour + day-of-week,
#      computed from history.csv, as a real short-term forecast.
#   3. Stretch: fit a simple trend (e.g. linear regression on the last
#      hour of points) to catch a station that's draining fast.
#   4. Bonus: rank nearby stations by predicted availability if this
#      one looks likely to be empty (needs a distance calc from lat/lon).
