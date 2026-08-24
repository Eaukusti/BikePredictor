# BikePredictor

**Helsinki City Bike Availability Predictor** — a real-time dashboard showing live bike station status and hourly predictions for the next 5 days. Built with HSL's Digitransit API, historical time-series analysis, and Streamlit.

Streamlit hosted version can be accessed here https://bikepredictor.streamlit.app

## Overview

Is there going to be a bike at your station when you need it? This app predicts short-term bike availability by blending live sensor readings with historical patterns. It tells you:
- **Right now**: How many bikes and free docks are currently available at any HSL station
- **Today**: Hourly prediction of bike availability for the rest of today
- **Next 4 days**: Daily patterns based on historical day-of-week and hour-of-day averages

## Features

### Live Status
- Real-time bike and dock counts from the HSL Digitransit API
- Coverage: 150+ stations across Helsinki and Espoo
- Station selector by name
- Visual metrics (bikes available, docks available, station capacity)

### Time-Series Forecasting
- **Today's chart**: Past readings (solid line) + future predictions (dashed line), with a red "now" marker
- **Upcoming days**: Five-day view with hourly predictions based on historical patterns
- **Intelligent baselines**: Tiered lookup (same weekday/hour → same day type/hour → same hour across all days → all data)
- **Recency decay**: Live reading influence fades over ~3 hours as predictions extend further ahead
- **Automatic fallback**: Shows "no data" gracefully when history is insufficient

### Nearby Stations
- Click "Find nearby stations" to discover alternatives within ~2 km
- Great-circle distance calculation with interactive table

## Architecture

```
Data Flow:
┌─────────────────────────┐
│  HSL Digitransit API    │  (GraphQL endpoint, real-time)
└────────────┬────────────┘
             │
      ┌──────▼──────────┐
      │ digitransit_    │  Fetch live station status
      │ client.py       │  (bikes, docks, capacity)
      └──────┬──────────┘
             │
      ┌──────┴──────────┐
      │                 │
   ┌──▼──────┐   ┌─────▼──────┐
   │ app.py  │   │ poll_and_  │  Snapshot station data
   │ (web)   │   │ log.py     │  Append to history.csv
   └──────────┘   └─────┬──────┘
                        │
                   ┌────▼─────────┐
                   │ history.csv  │  Time-series database
                   └────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │ timeseries.py     │  Aggregate into hourly grid
              │ predict.py        │  Generate predictions
              └───────────────────┘
```

**Two-tier architecture:**
1. **Web frontend** (`app.py`): Calls Digitransit API on every page load for live status
2. **Historical pipeline**: Separate scheduled poll (GitHub Actions, ~every 15 min) that builds `history.csv` over time

## How Predictions Work

The prediction algorithm in `predict.py` uses a **tiered baseline with exponential recency decay**:

1. **Baseline selection** (for each target hour):
   - Try: Historical average for (weekday, hour)
   - Fallback: Historical average for (day type [weekday/weekend], hour)
   - Fallback: Historical average for (hour, any day)
   - Fallback: Overall station average
   - If no history: Use current live reading

2. **Blend current + baseline**:
   ```
   prediction = recency_weight * current_value + (1 - recency_weight) * baseline
   ```
   where `recency_weight = exp(-hours_ahead / 3.0)`
   - At prediction time: 100% current reading
   - In 3 hours: ~37% current, ~63% historical baseline
   - In 6+ hours: mostly historical baseline

3. **Minimum data requirements**:
   - At least 2 observations needed before a tier is trusted
   - Ensures noisy data doesn't dominate early predictions

## Project Structure

```
BikePredictor/
├── app.py                        Main Streamlit web app
├── requirements.txt              Python dependencies
├── README.md                     This file
├── data/
│   └── history.csv               Time-series database (created by poll.yml)
└── src/
    ├── digitransit_client.py     HSL API wrapper
    ├── poll_and_log.py           Scheduled snapshot collector
    ├── predict.py                Hourly availability predictor
    ├── timeseries.py             Time-series aggregation helpers
    └── geo.py                    Distance calculations
```

### Module Details

**`digitransit_client.py`**
- Queries HSL's GraphQL API for all stations
- Handles availability data split by vehicle type (bike vs. scooter)
- Falls back to capacity-based dock availability when not directly available
- Returns: list of dicts with `stationId`, `name`, `lat`, `lon`, `bikes_available`, `docks_available`

**`poll_and_log.py`**
- Runs on schedule (GitHub Actions: every 15 min)
- Fetches all stations and appends a row to `history.csv`
- Creates file with header on first run
- Records: timestamp, station_id, name, bikes_available, docks_available

**`predict.py`**
- `predict_hourly()`: Main prediction function
  - Input: historical DataFrame, station name, future timestamps
  - Output: Series of predicted values aligned to target times
- `_baseline_for_hour()`: Tiered historical lookup
- Minimum 2 samples per tier to prevent outliers

**`timeseries.py`**
- `upcoming_days()`: Generate next N days with labels ("Today", "Tomorrow", etc.)
- `day_hour_index()`: Create 24-hour index for a given date (midnight to 23:00)
- `hourly_series()`: Resample raw snapshots into clean hourly grid for one station/day
  - Forward-fill gaps (missing hours = no change assumption)

**`geo.py`**
- `haversine_km()`: Great-circle distance between two lat/lon points
- `nearest_stations()`: Find N closest stations to a given location


## Key Design Decisions

### Why recency decay (vs. simple day-of-week average)?
A pure historical average works well if traffic is entirely predictable, but real bike stations have variance. By weighting the live reading more heavily near-term, we capture:
- Real-time fluctuations (e.g., "someone just took the last bike")
- Anomalies (e.g., maintenance, events) that haven't happened before
- Gradual transitions toward baseline patterns

### Why tiered baselines (vs. single historical grouping)?
Different time granularities matter for different predictions:
- For "Monday 8 AM", a Monday 8 AM average is most relevant (commute pattern)
- If few Mondays exist, weekday 8 AM captures the general morning trend
- If we need fallback, hour-of-day captures circadian rhythm
- Overall average is the safety net

### Why 3-hour decay window?
Bike availability changes on predictable cycles: commute peaks, lunch, evening. A 3-hour window means:
- Immediate predictions (next hour) are ~85% live reading
- Mid-morning predictions (3 hours ahead) balance both signals equally
- Long-term predictions (6+ hours) mostly trust the historical pattern

This is tunable; you could experiment with shorter decay for more reactive predictions.

## Data Collection Notes

- **Latency**: API polls run on a 15-minute schedule and is additionally limited by GitHub's servers resulting in an approx hourly data feed. High-frequency changes within minutes won't be captured.
- **Gaps**: If a poll fails or is skipped, `hourly_series()` forward-fills the previous value. This assumes "no change" rather than missing data.
- **Station churn**: New stations occasionally appear in the HSL network. Once they're in `history.csv`, predictions work for them.
- **Schema stability**: HSL's GraphQL schema is versioned, but the exact field names can change. The GraphiQL explorer (linked in `digitransit_client.py`) is the source of truth.

## Future Improvements

- **User location**: Geolocation-based station suggestions
- **Multiple predictions**: Compare strategies (baseline only, live only, weighted blend)
- **Performance optimization**: Cache history, index by station for faster lookups
