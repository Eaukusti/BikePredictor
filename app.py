"""
Helsinki City Bike Availability — live status + hourly outlook.
Run locally with: streamlit run app.py
"""
import altair as alt
import pandas as pd
import streamlit as st

from src.digitransit_client import fetch_stations
from src.geo import nearest_stations
from src.timeseries import upcoming_days, hourly_series, day_hour_index, TZ
from src.predict import predict_hourly

st.set_page_config(page_title="Helsinki City Bikes", page_icon="🚲", layout="centered")
st.title("🚲 Helsinki City Bike Availability")

stations = fetch_stations()
df = pd.DataFrame(stations)
all_names = sorted(df["name"].unique())

# Apply any pending station change (e.g. from clicking a nearest-station
# row) BEFORE the selectbox is created — session_state for a keyed widget
# can't be modified after that widget has already been instantiated.
if "pending_station" in st.session_state:
    st.session_state.selected_station = st.session_state.pop("pending_station")

if "selected_station" not in st.session_state or st.session_state.selected_station not in all_names:
    st.session_state.selected_station = all_names[0]

station_name = st.selectbox("Pick a station", all_names, key="selected_station")

row = df[df["name"] == station_name].iloc[0]

st.markdown(f"""
<div style="display:flex; gap:2.5rem; margin-bottom:1rem;">
  <div>
    <div style="color:gray; font-size:0.9rem;">Bikes available now</div>
    <div style="font-size:2rem; font-weight:600;">{int(row['bikes_available'])}</div>
  </div>
  <div>
    <div style="color:gray; font-size:0.9rem;">Free docks now</div>
    <div style="font-size:2rem; font-weight:600;">{int(row['docks_available'])}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# Fixed y-axis (0 to station capacity), used on every chart below
capacity = row.get("capacity")
if pd.notna(capacity):
    capacity = int(capacity)
    y_scale = alt.Scale(domain=[0, capacity])
    y_axis = alt.Axis(title="Bikes available", values=list(range(0, capacity + 1)), tickMinStep=1)
else:
    y_scale = alt.Undefined
    y_axis = alt.Axis(title="Bikes available")

st.subheader("Availability")
try:
    hist = pd.read_csv("data/history.csv")
    hist["timestamp"] = pd.to_datetime(hist["timestamp"], utc=True)
except FileNotFoundError:
    hist = None

if hist is None or hist.empty:
    st.info("No history yet — the GitHub Action needs to run a few times first.")
else:
    has_any_history = not hist[hist["name"] == station_name].empty

    days = upcoming_days(n=5)
    tabs = st.tabs([label for _, label in days])

    for tab, (day, label) in zip(tabs, days):
        with tab:
            if not has_any_history:
                st.info("Prediction not built yet for this day — not enough history.")
                continue

            now = pd.Timestamp.now(tz=TZ)
            current_value = int(row["bikes_available"])

            if label == "Today":
                series = hourly_series(hist, station_name, "bikes_available", day)
                if series is None or series.dropna().empty:
                    st.info("No data for this station yet.")
                    continue

                past = series[series.index < now].reset_index()
                past.columns = ["hour", "bikes_available"]
                now_point = pd.DataFrame({"hour": [now], "bikes_available": [current_value]})
                past = pd.concat([past, now_point], ignore_index=True)

                future_hours = series.index[series.index > now]
                predicted = predict_hourly(
                    hist, station_name, "bikes_available", future_hours, now, current_value
                )
                future_predicted = predicted.reset_index()
                future_predicted.columns = ["hour", "bikes_available"]
                future = pd.concat([now_point, future_predicted], ignore_index=True)

                past_line = alt.Chart(past).mark_line(color="#1f77b4").encode(
                    x=alt.X("hour:T", title="Hour", axis=alt.Axis(format="%H:%M")),
                    y=alt.Y("bikes_available:Q", scale=y_scale, axis=y_axis),
                )
                future_line = alt.Chart(future).mark_line(color="#1f77b4", strokeDash=[4, 4]).encode(
                    x="hour:T",
                    y=alt.Y("bikes_available:Q", scale=y_scale, axis=y_axis),
                )
                rule = alt.Chart(pd.DataFrame({"hour": [now]})).mark_rule(
                    color="red", strokeDash=[4, 4]
                ).encode(x="hour:T")

                st.altair_chart((past_line + future_line + rule), use_container_width=True)
                st.caption(f"Red line: right now ({now:%H:%M}). Dotted: forecast for the rest of today.")

            else:
                target_times = day_hour_index(day)
                predicted = predict_hourly(
                    hist, station_name, "bikes_available", target_times, now, current_value
                )
                future = predicted.reset_index()
                future.columns = ["hour", "bikes_available"]

                future_line = alt.Chart(future).mark_line(color="#1f77b4", strokeDash=[4, 4]).encode(
                    x=alt.X("hour:T", title="Hour", axis=alt.Axis(format="%H:%M")),
                    y=alt.Y("bikes_available:Q", scale=y_scale, axis=y_axis),
                )
                st.altair_chart(future_line, use_container_width=True)
                st.caption(f"Forecast for {label} — accuracy improves as more history accumulates.")

st.subheader(f"Nearest stations to {station_name}")
nearby = nearest_stations(df, row, n=5)

for _, nearby_row in nearby.iterrows():
    label = (
        f"{nearby_row['name']} — {nearby_row['distance_km']:.2f} km · "
        f"{int(nearby_row['bikes_available'])} bikes · {int(nearby_row['docks_available'])} docks"
    )
    clicked = st.button(label, key=f"nearest_btn_{nearby_row['name']}", use_container_width=True)

    if clicked:
        st.session_state.pending_station = nearby_row["name"]
        st.rerun()



