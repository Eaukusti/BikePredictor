"""
Thin wrapper around HSL's Digitransit GraphQL API for live city bike
station status (Helsinki + Espoo).

Docs:   https://digitransit.fi/en/developers/apis/1-routing-api/bicycles-scooters-cars/
Explore queries interactively (recommended before writing code):
        https://digitransit.fi/en/developers/apis/1-routing-api/1-graphiql/
Get a free API key:
        https://portal-api.digitransit.fi/

NOTE: GraphQL schemas evolve. If a field below errors out, open the
GraphiQL explorer above, paste QUERY_ALL_STATIONS in, and check the
schema docs on the right-hand panel for the current field names.
"""
import os
import requests

ENDPOINT = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"

QUERY_ALL_STATIONS = """
{
  vehicleRentalStations {
    stationId
    name
    lat
    lon
    capacity
    availableVehicles {
      byType {
        count
        vehicleType { formFactor }
      }
    }
    availableSpaces {
      byType {
        count
        vehicleType { formFactor }
      }
    }
  }
}
"""


def _sum_counts(by_type_list):
    """availableVehicles/availableSpaces come back split 'by type' (e.g.
    bicycle vs. scooter). For plain city bikes there's usually one type,
    but we sum defensively in case a station reports more than one."""
    return sum(item["count"] for item in by_type_list)


def fetch_stations() -> list[dict]:
    """Return current status of every HSL city bike station as a list of
    dicts: stationId, name, lat, lon, bikes_available, docks_available."""
    api_key = os.environ.get("DIGITRANSIT_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set the DIGITRANSIT_API_KEY environment variable "
            "(get a free key at https://portal-api.digitransit.fi/)"
        )

    headers = {
        "Content-Type": "application/json",
        "digitransit-subscription-key": api_key,
    }
    resp = requests.post(
        ENDPOINT,
        json={"query": QUERY_ALL_STATIONS},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    stations = resp.json()["data"]["vehicleRentalStations"]


    for s in stations:
        s["bikes_available"] = _sum_counts(s["availableVehicles"]["byType"])
        spaces = _sum_counts(s["availableSpaces"]["byType"])
        if spaces == 0 and s.get("capacity") is not None:
            # availableSpaces.byType comes back empty for this feed —
            # fall back to capacity minus bikes currently docked
            spaces = max(s["capacity"] - s["bikes_available"], 0)
        s["docks_available"] = spaces

    return stations


if __name__ == "__main__":
    # Quick manual test: `python src/digitransit_client.py`
    for s in fetch_stations()[:5]:
        print(f"{s['name']:<30} bikes={s['bikes_available']:<3} docks={s['docks_available']}")
