"""
Time-series helpers: turning raw polled snapshots into a clean hourly
grid per day, for the day-by-day chart in app.py.
"""
from datetime import timedelta
import pandas as pd

TZ = "Europe/Helsinki"


def upcoming_days(n=5, tz=TZ):
    """Return n (date, label) pairs starting today, in local time.
    Labels: 'Today', 'Tomorrow', then weekday names (e.g. 'Friday')."""
    today = pd.Timestamp.now(tz=tz).normalize().date()
    days = []
    for i in range(n):
        d = today + timedelta(days=i)
        if i == 0:
            label = "Today"
        elif i == 1:
            label = "Tomorrow"
        else:
            label = d.strftime("%A")
        days.append((d, label))
    return days


def day_hour_index(target_date, tz=TZ):
    """The 24 hourly timestamps (midnight to 23:00, local time) for one date."""
    day_start = pd.Timestamp(target_date, tz=tz)
    return pd.date_range(day_start, periods=24, freq="h")


def hourly_series(history_df, station_name, value_col, target_date, tz=TZ):
    """Return a 24-point hourly Series (local time, midnight to 23:00) for
    one station/day, built from raw polled snapshots.

    Gaps are filled by carrying the previous known value forward — a
    missing hour means 'nothing changed since the last real reading',
    not 'no data'.
    """
    station_hist = history_df[history_df["name"] == station_name].copy()
    if station_hist.empty:
        return None

    s = station_hist.set_index("timestamp")[value_col].sort_index()
    s = s.tz_convert(tz)

    day_index = day_hour_index(target_date, tz)

    hourly_all = s.resample("h").last()
    combined_index = hourly_all.index.union(day_index)
    hourly_all = hourly_all.reindex(combined_index).ffill()

    return hourly_all.reindex(day_index)
