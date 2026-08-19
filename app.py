"""
Helsinki City Bike Availability — live status + short-term outlook.
Run locally with: streamlit run app.py
"""
import pandas as pd
import streamlit as st
import altair as alt

from src.digitransit_client import fetch_stations
from src.geo import nearest_stations
from src.timeseries import upcoming_days, hourly_series

st.set_page_config(page_title="Helsinki City Bikes", page_icon="🚲", layout="centered")
st.title("🚲 Helsinki City Bike Availability")

stations = fetch_stations()
df = pd.DataFrame(stations)
all_names = sorted(df["name"].unique())

station_name = st.selectbox("Pick a station", all_names)
row = df[df["name"] == station_name].iloc[0]

col1, col2 = st.columns(2)
col1.metric("Bikes available now", int(row["bikes_available"]))
col2.metric("Free docks now", int(row["docks_available"]))

st.subheader(f"Nearest stations to {station_name}")
nearby = nearest_stations(df, row, n=5)
st.dataframe(
    nearby[["name", "distance_km", "bikes_available", "docks_available"]]
    .rename(columns={
        "name": "Station", "distance_km": "Distance (km)",
        "bikes_available": "Bikes", "docks_available": "Docks",
    })
    .round({"Distance (km)": 2}),
    hide_index=True,
)

st.subheader("Availability")
try:
    hist = pd.read_csv("data/history.csv")
    hist["timestamp"] = pd.to_datetime(hist["timestamp"], utc=True)
except FileNotFoundError:
    hist = None

if hist is None or hist.empty:
    st.info("No history yet — the GitHub Action needs to run a few times first.")
else:
    days = upcoming_days(n=5)
    tabs = st.tabs([label for _, label in days])

    for tab, (day, label) in zip(tabs, days):
        with tab:
            if label != "Today":
                st.info("Prediction not built yet — check back once there's more history.")
                continue

            series = hourly_series(hist, station_name, "bikes_available", day)
            if series is None or series.dropna().empty:
                st.info("No data for this station yet.")
                continue

            chart_df = series.reset_index()
            chart_df.columns = ["hour", "bikes_available"]

            line = alt.Chart(chart_df).mark_line(point=True).encode(
                x=alt.X("hour:T", title="Hour", axis=alt.Axis(format="%H:%M")),
                y=alt.Y("bikes_available:Q", title="Bikes available"),
            )

            last_ts = hist[hist["name"] == station_name]["timestamp"].max()
            last_ts_local = last_ts.tz_convert("Europe/Helsinki")
            rule_df = pd.DataFrame({"hour": [last_ts_local]})
            rule = alt.Chart(rule_df).mark_rule(color="red", strokeDash=[4, 4]).encode(x="hour:T")

            st.altair_chart((line + rule).interactive(), use_container_width=True)
            st.caption(f"Dashed red line: most recent measurement, {last_ts_local:%H:%M} local time")

# TODO: hook up real predictions for Tomorrow / Fri / Sat / Sun once
# there's enough history for a day-of-week + hour baseline (see README)


# TODO: prediction logic (see README)
