"""
Helsinki City Bike Availability — live status + short-term outlook.
Run locally with: streamlit run app.py
"""
import pandas as pd
import streamlit as st

from src.digitransit_client import fetch_stations
from src.favorites import load_favorites, save_favorites, nearest_stations

st.set_page_config(page_title="Helsinki City Bikes", page_icon="🚲", layout="centered")
st.title("🚲 Helsinki City Bike Availability")

stations = fetch_stations()
df = pd.DataFrame(stations)
all_names = sorted(df["name"].unique())

if "selected_station" not in st.session_state:
    st.session_state.selected_station = all_names[0]
if st.session_state.selected_station not in all_names:
    st.session_state.selected_station = all_names[0]

favorites = load_favorites()

if favorites:
    st.subheader("⭐ Your favorites")
    cols = st.columns(len(favorites))
    for col, fav in zip(cols, favorites):
        if fav in all_names and col.button(fav):
            st.session_state.selected_station = fav
else:
    st.caption("No favorites yet — pick a station below and star it.")

station_name = st.selectbox(
    "Or pick any station",
    all_names,
    index=all_names.index(st.session_state.selected_station),
)
st.session_state.selected_station = station_name
row = df[df["name"] == station_name].iloc[0]

is_favorite = station_name in favorites
star_label = "★ Remove from favorites" if is_favorite else "☆ Add to favorites"
if st.button(star_label):
    if is_favorite:
        favorites.remove(station_name)
    else:
        favorites.append(station_name)
    save_favorites(favorites)
    st.rerun

col1, col2 = st.columns(2)
col1.metric("Bikes available now", int(row["bikes_available"]))
col2.metric("Free docks now", int(row["docks_available"]))

if is_favorite:
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

st.subheader("Recent trend")
try:
    hist = pd.read_csv("data/history.csv", parse_dates=["timestamp"])
    station_hist = hist[hist["name"] == station_name].tail(48)
    if station_hist.empty:
        st.info("No history for this station yet.")
    else:
        st.line_chart(station_hist.set_index("timestamp")["bikes_available"])
except FileNotFoundError:
    st.info("No history yet — the GitHub Action needs to run a few times first.")

# TODO: prediction logic (see README)
