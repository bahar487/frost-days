import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import pandas as pd
import numpy as np
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "data"
VALIDATION_DIR = Path(__file__).resolve().parent / "validation"
VALIDATION_DIR.mkdir(exist_ok=True)

GEO_API_URL = "https://geo.api.gouv.fr/communes"
DATE_START = "2013-01-01"
DATE_END = "2024-12-31"

VILLES = [
    ("Asnières-sur-Saône", "01", "Asnières-sur-Saône_01"),
    ("Digne-les-Bains", "04", "Digne-les-Bains_04"),
    ("Espinchal", "63", "Espinchal_63"),
    ("Marseille", "13", "Marseille_13"),
    ("Montfalcon", "38", "Montfalcon_38"),
    ("Paris", "75", "Paris_75"),
]

def get_meteo_url(dept):
    dept2 = dept.zfill(2)
    r = requests.get("https://www.data.gouv.fr/api/1/datasets/donnees-climatologiques-de-base-quotidiennes/", timeout=30)
    for res in r.json().get("resources", []):
        u = res.get("url", "")
        if f"Q_{dept2}_previous" in u and "RR-T-Vent" in u:
            return u
    return None

def load_meteo_dept(dept):
    dept2 = dept.zfill(2)
    gz_path = BASE_DIR / f"meteo_{dept2}.csv.gz"
    if not gz_path.exists():
        url = get_meteo_url(dept)
        if not url:
            raise RuntimeError(f"URL introuvable pour dept {dept2}")
        print(f"  Telechargement dept {dept2}...")
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(gz_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*256):
                f.write(chunk)
    print(f"  Lecture CSV dept {dept2}...")
    df = pd.read_csv(gz_path, sep=";", encoding="latin-1", low_memory=False, compression="gzip")
    df.columns = df.columns.str.strip().str.upper()
    df["station_id"] = df["NUM_POSTE"].astype(str).str.zfill(8)
    df["date"] = pd.to_datetime(df["AAAAMMJJ"].astype(str), format="%Y%m%d", errors="coerce")
    df["tmin"] = pd.to_numeric(df["TN"], errors="coerce") / 10.0
    df["latitude"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["LON"], errors="coerce")
    df["alti"] = pd.to_numeric(df["ALTI"], errors="coerce")
    df["station_name"] = df["NOM_USUEL"].astype(str).str.strip()
    df = df.dropna(subset=["date"])
    return df

def find_nearest_station(commune_name, dept, stations):
    try:
        params = {"nom": commune_name, "codeDepartement": dept.zfill(2), "fields": "nom,centre", "format": "json", "geometry": "centre", "limit": 1}
        r = requests.get(GEO_API_URL, params=params, timeout=10)
        data = r.json()
        if not data:
            return None
        coords = data[0].get("centre", {}).get("coordinates")
        if not coords:
            return None
        lon, lat = coords
    except:
        return None
    lats = stations["latitude"].values.astype(float)
    lons = stations["longitude"].values.astype(float)
    R = 6371.0
    lat1_r = np.radians(lat)
    dlat = np.radians(lats) - lat1_r
    dlon = np.radians(lons) - np.radians(lon)
    a = np.sin(dlat/2)**2 + np.cos(lat1_r)*np.cos(np.radians(lats))*np.sin(dlon/2)**2
    dist = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return stations.iloc[np.argmin(dist)]["station_id"]

print("=== Generation des fichiers de validation ===\n")
all_stations = {}

for commune, dept, fname in VILLES:
    print(f"[{commune} / dept {dept}]")
    try:
        meteo = load_meteo_dept(dept)
        # Garder uniquement les stations avec donnees recentes
        recent_sids = meteo[meteo["date"].dt.year >= 2013]["station_id"].unique()
        meteo_recent = meteo[meteo["station_id"].isin(recent_sids)]
        stations = meteo_recent[["station_id","station_name","latitude","longitude","alti"]].drop_duplicates("station_id").dropna(subset=["latitude","longitude"])
        all_stations[dept] = stations
        sid = find_nearest_station(commune, dept, stations)
        if not sid:
            sid = stations["station_id"].iloc[0]
        df = meteo[(meteo["station_id"]==sid) & (meteo["date"]>=DATE_START) & (meteo["date"]<=DATE_END)].copy()
        df = df.sort_values("date")
        df["frost_day"] = df["tmin"] <= 0.0
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day
        out = df[["station_id","station_name","latitude","longitude","alti","date","tmin","frost_day","year","month","day"]].copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out.to_csv(VALIDATION_DIR / f"{fname}_complete.csv", index=False)
        print(f"  -> {len(out)} lignes, station: {sid}")
    except Exception as e:
        print(f"  ERREUR: {e}")

print("\n  Generating stations_df_complete.csv...")
frames = [s[["station_id","station_name"]].drop_duplicates("station_id") for s in all_stations.values()]
pd.concat(frames).drop_duplicates("station_id").sort_values("station_id").to_csv(VALIDATION_DIR / "stations_df_complete.csv", index=False)

print("  Generating city_df_complete.csv...")
try:
    r = requests.get("https://geo.api.gouv.fr/communes?fields=code,nom,codeDepartement,departement,centre&format=json&geometry=centre&limit=36000", timeout=60)
    rows = []
    for c in r.json():
        coords = c.get("centre", {}).get("coordinates", [None, None])
        rows.append({"insee_code": c.get("code",""), "name": c.get("nom",""), "dep_code": c.get("codeDepartement",""), "dep_name": c.get("departement",{}).get("nom","") if isinstance(c.get("departement"),dict) else "", "lat": round(coords[1],3) if coords[1] else None, "lon": round(coords[0],3) if coords[0] else None})
    pd.DataFrame(rows).to_csv(VALIDATION_DIR / "city_df_complete.csv", index=False)
    print(f"  -> {len(rows)} lignes")
except Exception as e:
    print(f"  ERREUR city_df: {e}")

print("\n=== Termine ! ===")
