"""
Predicted hourly bike availability: blends the live current reading with
a tiered historical baseline for each target hour. The current reading's
influence decays the further ahead the prediction is.
"""
import numpy as np
import pandas as pd

MIN_SAMPLES = 2    # minimum observations before a tier is trusted
DECAY_HOURS = 6.0  # roughly how many hours ahead 'recency' stays meaningful


def _baseline_for_hour(history_station, weekday, hour, value_col):
    """Tiered historical average for one (weekday, hour). Falls back to
    coarser groupings as needed. Returns None if there's no data at all."""
    df = history_station.copy()
    df["weekday"] = df["timestamp"].dt.dayofweek  # 0=Mon ... 6=Sun
    df["hour"] = df["timestamp"].dt.hour
    df["is_weekend"] = df["weekday"] >= 5

    same = df[(df["weekday"] == weekday) & (df["hour"] == hour)]
    if len(same) >= MIN_SAMPLES:
        return same[value_col].mean()

    is_weekend = weekday >= 5
    same_type = df[(df["is_weekend"] == is_weekend) & (df["hour"] == hour)]
    if len(same_type) >= MIN_SAMPLES:
        return same_type[value_col].mean()

    same_hour = df[df["hour"] == hour]
    if len(same_hour) >= MIN_SAMPLES:
        return same_hour[value_col].mean()

    if len(df) > 0:
        return df[value_col].mean()

    return None


def predict_hourly(history_df, station_name, value_col, target_times, now, current_value):
    """Predict value_col at each timestamp in target_times (future relative
    to `now`), blending the live current_value with a historical baseline.
    Returns a Series indexed by target_times."""
    station_hist = history_df[history_df["name"] == station_name]

    predictions = []
    for t in target_times:
        hours_ahead = max((t - now).total_seconds() / 3600.0, 0)
        baseline = _baseline_for_hour(station_hist, t.dayofweek, t.hour, value_col)

        if baseline is None:
            predictions.append(current_value)  # no history yet — best guess is "no change"
            continue

        recency_weight = np.exp(-hours_ahead / DECAY_HOURS)
        predictions.append(recency_weight * current_value + (1 - recency_weight) * baseline)

    return pd.Series(predictions, index=target_times, name=value_col)
