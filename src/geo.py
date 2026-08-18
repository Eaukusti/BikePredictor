"""
Geo helpers — great-circle distance and nearest-station lookup.
"""
from math import radians, sin, cos, sqrt, atan2


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two lat/lon points, in km."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def nearest_stations(df, station_row, n=5):
    """Given the full stations DataFrame and the row for one station,
    return the n closest other stations with a 'distance_km' column added."""
    others = df[df["stationId"] != station_row["stationId"]].copy()
    others["distance_km"] = others.apply(
        lambda r: haversine_km(station_row["lat"], station_row["lon"], r["lat"], r["lon"]),
        axis=1,
    )
    return others.sort_values("distance_km").head(n)
