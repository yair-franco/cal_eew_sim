"""
get_mmi_polygon.py

Fetches the USGS ShakeAlert summary JSON and extracts polygon coordinates
for a feature matching a given name (e.g. "MMI 3", "MMI 3.5", "Initial MMI 3.5").

Name matching strategy (in order of priority):
  1. Exact match (case-insensitive)
  2. Numeric MMI value match — extracts the number from both the target and
     each feature name, so "MMI 3", "MMI 3.0", and "MMI 3.5" are all distinct
     but "MMI 3" and "mmi 3.0" are treated as equal.
"""

import json
import re
import urllib.request

URL = "https://earthquake.usgs.gov/product/shake-alert/ew1776130160/ew/1776130485682/summary.json"
TARGET_NAME = "MMI 3"  # Change this to any name you want to search for


def fetch_summary(url: str) -> dict:
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def extract_mmi_value(name: str) -> float | None:
    """
    Pull the numeric MMI value out of a feature name string.
    Handles formats like "MMI 3", "MMI 3.0", "MMI 3.5", "Initial MMI 3.5".
    Returns a float, or None if no number is found.
    """
    match = re.search(r"MMI\s+([\d.]+)", name, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def names_match(feature_name: str, target_name: str) -> bool:
    """
    Return True if feature_name matches target_name by either:
      1. Exact case-insensitive string match, or
      2. Both contain an MMI value and those values are numerically equal.
    """
    if feature_name.lower() == target_name.lower():
        return True

    target_val = extract_mmi_value(target_name)
    feature_val = extract_mmi_value(feature_name)
    if target_val is not None and feature_val is not None:
        return target_val == feature_val

    return False


def find_polygon(data: dict, target_name: str) -> list | None:
    """
    Search all alert FeatureCollections for a Polygon feature whose name
    matches target_name using names_match(). Returns coordinates if found.
    """
    for collection in data.get("alerts", []):
        collection_id = collection.get("id", "unknown")
        for feature in collection.get("features", []):
            name = feature.get("properties", {}).get("name", "")
            if names_match(name, target_name):
                geometry = feature.get("geometry", {})
                if geometry.get("type") == "Polygon":
                    print(f"Found '{name}' in collection: {collection_id}")
                    return geometry["coordinates"]

    return None


def list_all_polygon_names(data: dict) -> list[str]:
    """Return all feature names that have Polygon geometry across all collections."""
    names = []
    for collection in data.get("alerts", []):
        collection_id = collection.get("id", "unknown")
        for feature in collection.get("features", []):
            if feature.get("geometry", {}).get("type") == "Polygon":
                name = feature.get("properties", {}).get("name", "<unnamed>")
                names.append(f"  [{collection_id}] {name}")
    return names


def main():
    print(f"Fetching: {URL}\n")
    data = fetch_summary(URL)

    coords = find_polygon(data, TARGET_NAME)

    if coords:
        # coords is a list of rings; the first ring is the exterior boundary.
        # Each point is [longitude, latitude].
        exterior_ring = coords[0]
        print(f"\nPolygon coordinates for '{TARGET_NAME}':")
        print(f"  Number of vertices: {len(exterior_ring)}")
        print(f"  Format: [longitude, latitude]\n")
        for i, point in enumerate(exterior_ring):
            lon, lat = point
            print(f"  Point {i+1:>2}: lon={lon}, lat={lat}")

        # Also return as a plain list of (lat, lon) tuples if useful downstream
        latlon_pairs = [(pt[1], pt[0]) for pt in exterior_ring]
        print(f"\n  As (lat, lon) tuples: {latlon_pairs}")
    else:
        print(f"No Polygon feature named '{TARGET_NAME}' was found.\n")
        print("Available polygon feature names:")
        for name in list_all_polygon_names(data):
            print(name)


if __name__ == "__main__":
    main()