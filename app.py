"""
Helsinki City Bike Availability — live status + hourly outlook.
Run locally with: streamlit run app.py
"""
import altair as alt
import pandas as pd
import streamlit as st

from src.digitransit_client import fetch_stations
from src.geo import nearest_stations
from src.timeseries import upcoming_days, hourly_series, TZ
from src.predict import predict_hourly

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
                st.info("Prediction not built yet for this day — coming soon.")
                continue

            now = pd.Timestamp.now(tz=TZ)
            current_value = int(row["bikes_available"])
            #decay_hours = st.slider("Decay hours (debug)", 1.0, 24.0, 6.0, step=0.5) #commented out for now, but could be useful for debugging

            series = hourly_series(hist, station_name, "bikes_available", day)
            if series is None or series.dropna().empty:
                st.info("No data for this station yet.")
                continue

            # Solid line: real history up to right now. The last point is
            # replaced with the true live reading, so it always matches the
            # "Bikes available now" metric above exactly.
            past = series[series.index < now].reset_index()
            past.columns = ["hour", "bikes_available"]
            now_point = pd.DataFrame({"hour": [now], "bikes_available": [current_value]})
            past = pd.concat([past, now_point], ignore_index=True)

            # Dotted line: forecast for the rest of today, starting from that
            # same live point so it connects with no visual gap.
            future_hours = series.index[series.index > now]
            predicted = predict_hourly(hist, station_name, "bikes_available", future_hours, now, current_value)
            future = pd.concat([
                now_point,
                predicted.reset_index().rename(columns={"index": "hour", "bikes_available": "bikes_available"}),
            ], ignore_index=True)

            past_line = alt.Chart(past).mark_line(color="#1f77b4").encode(
                x=alt.X("hour:T", title="Hour", axis=alt.Axis(format="%H:%M")),
                y=alt.Y("bikes_available:Q", title="Bikes available"),
            )
            future_line = alt.Chart(future).mark_line(color="#1f77b4", strokeDash=[4, 4]).encode(
                x="hour:T", y="bikes_available:Q",
            )
            rule = alt.Chart(pd.DataFrame({"hour": [now]})).mark_rule(
                color="red", strokeDash=[4, 4]
            ).encode(x="hour:T")

            st.altair_chart((past_line + future_line + rule).interactive(), use_container_width=True)
            st.caption(f"Red line: right now ({now:%H:%M}). Dotted: forecast for the rest of today.")
