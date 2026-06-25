import requests
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "data"
BASE_DIR.mkdir(exist_ok=True)

GEO_API_URL = "https://geo.api.gouv.fr/communes"
DATASET_ID = "donnees-climatologiques-de-base-quotidiennes"
DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets"

MISSING_CITIES = {
    "Marseille": [43.295, 5.372],
    "Paris": [48.866, 2.333],
    "Lyon": [45.75, 4.85],
}

def find_commune_coords(commune_name, dept_code):
    for ville, coords in MISSING_CITIES.items():
        if ville.lower() == commune_name.strip().lower():
            return coords[0], coords[1]
    try:
        params = {"nom": commune_name, "codeDepartement": dept_code.zfill(2), "fields": "nom,centre", "format": "json", "geometry": "centre", "limit": 5}
        r = requests.get(GEO_API_URL, params=params, timeout=10)
        data = r.json()
        if data:
            coords = data[0].get("centre", {}).get("coordinates", None)
            if coords:
                return coords[1], coords[0]
    except Exception as e:
        print(f"API error: {e}")
    return None, None

def get_meteo_url(dept):
    dept2 = dept.zfill(2)
    try:
        url = f"{DATAGOUV_API}/{DATASET_ID}/resources/?page_size=500"
        r = requests.get(url, timeout=30)
        resources = r.json().get("data", [])
        keyword = f"Q_{dept2}_previous-1950-2024"
        for res in resources:
            title = res.get("title", "") + res.get("url", "")
            if keyword in title or f"_{dept2}_" in title:
                return res.get("url")
    except Exception as e:
        print(f"API resources error: {e}")
    return None

def load_communes():
    return pd.DataFrame(columns=["nom_commune", "code_departement", "lat", "lon"])

def load_stations():
    return pd.DataFrame(columns=["station_id", "lat", "lon"])

def load_meteo_dept(dept, year_start, year_end):
    dept2 = dept.zfill(2)
    cache_path = BASE_DIR / f"meteo_{dept2}.parquet"
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        mask = (df["date"].dt.year >= year_start) & (df["date"].dt.year <= year_end)
        return df[mask]
    gz_path = BASE_DIR / f"meteo_{dept2}.csv.gz"
    if not gz_path.exists():
        url = get_meteo_url(dept)
        if not url:
            raise RuntimeError(f"Impossible de trouver le fichier meteo pour dept {dept2}")
        print(f"  Download: {url}")
        r = requests.get(url, stream=True, timeout=300)
        r.raise_for_status()
        with open(gz_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*256):
                f.write(chunk)
    try:
        df = pd.read_csv(gz_path, sep=";", encoding="latin-1", low_memory=False, compression="gzip")
        df.columns = df.columns.str.strip().str.upper()
        df["station_id"] = df["NUM_POSTE"].astype(str).str.zfill(8)
        df["date"] = pd.to_datetime(df["AAAAMMJJ"].astype(str), format="%Y%m%d", errors="coerce")
        df["tn"] = pd.to_numeric(df["TN"], errors="coerce") / 10.0
        df["lat"] = pd.to_numeric(df["LAT"], errors="coerce")
        df["lon"] = pd.to_numeric(df["LON"], errors="coerce")
        stations = df[["station_id", "lat", "lon"]].drop_duplicates("station_id").dropna()
        stations.to_parquet(BASE_DIR / f"stations_{dept2}.parquet", index=False)
        result = df.dropna(subset=["date"])[["station_id", "date", "tn"]]
        result.to_parquet(cache_path, index=False)
        mask = (result["date"].dt.year >= year_start) & (result["date"].dt.year <= year_end)
        return result[mask]
    except Exception as e:
        raise RuntimeError(f"Erreur lecture meteo dept {dept2}: {e}")

def load_stations_from_dept(dept):
    dept2 = dept.zfill(2)
    cache_path = BASE_DIR / f"stations_{dept2}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    return pd.DataFrame(columns=["station_id", "lat", "lon"])
