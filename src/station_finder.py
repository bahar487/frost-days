"""
station_finder.py
Trouve les stations météo les plus proches d'une commune via la formule Haversine.
"""

import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en km entre deux points GPS (formule de Haversine)."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def haversine_vectorized(lat1: float, lon1: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Version vectorisée : distance de (lat1, lon1) vers un tableau de points."""
    R = 6371.0
    lat1_r = radians(lat1)
    lon1_r = radians(lon1)
    lats_r = np.radians(lats)
    lons_r = np.radians(lons)
    dlat = lats_r - lat1_r
    dlon = lons_r - lon1_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lats_r) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def find_nearest_stations(
    commune_lat: float,
    commune_lon: float,
    stations_df: pd.DataFrame,
    n: int = 5,
    max_dist_km: float = 100.0,
) -> pd.DataFrame:
    """
    Retourne les n stations les plus proches (dans un rayon max_dist_km).
    stations_df doit avoir colonnes : station_id, lat, lon
    """
    if stations_df.empty:
        return pd.DataFrame(columns=["station_id", "lat", "lon", "distance_km"])

    lats = stations_df["lat"].values.astype(float)
    lons = stations_df["lon"].values.astype(float)

    distances = haversine_vectorized(commune_lat, commune_lon, lats, lons)

    result = stations_df.copy()
    result["distance_km"] = distances
    result = result[result["distance_km"] <= max_dist_km]
    result = result.sort_values("distance_km").head(n).reset_index(drop=True)
    return result
