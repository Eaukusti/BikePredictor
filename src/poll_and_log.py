"""
Snapshot every station's status right now and append it to
data/history.csv. Meant to be run on a schedule (see
.github/workflows/poll.yml) so the file slowly accumulates real history
instead of being a one-time download.
"""
import csv
import os
from datetime import datetime, timezone

from digitransit_client import fetch_stations

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "history.csv")
FIELDS = ["timestamp", "station_id", "name", "bikes_available", "docks_available"]


def main():
    stations = fetch_stations()
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")

    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    file_exists = os.path.exists(HISTORY_FILE)

    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        for s in stations:
            writer.writerow({
                "timestamp": now,
                "station_id": s["stationId"],
                "name": s["name"],
                "bikes_available": s["bikes_available"],
                "docks_available": s["docks_available"],
            })

    print(f"Logged {len(stations)} stations at {now}")


if __name__ == "__main__":
    main()
