import pandas as pd
from data_loader import find_commune_coords, load_meteo_dept, load_stations_from_dept
from station_finder import find_nearest_stations
from frost_engine import compute_frost_days, get_monthly_summary, get_yearly_summary

def run_frost_analysis(commune_name, dept_code, date_start, date_end, n_stations=5, max_dist_km=100.0):
    date_start_ts = pd.Timestamp(date_start)
    date_end_ts = pd.Timestamp(date_end)
    year_start = date_start_ts.year
    year_end = date_end_ts.year
    commune_lat, commune_lon = find_commune_coords(commune_name, dept_code)
    if commune_lat is None:
        return {"error": f"Commune '{commune_name}' introuvable dans le departement {dept_code}."}
    try:
        meteo_df = load_meteo_dept(dept_code, year_start, year_end)
    except RuntimeError as e:
        return {"error": str(e)}
    stations_df = load_stations_from_dept(dept_code)
    if stations_df.empty:
        return {"error": "Aucune station meteo trouvee pour ce departement."}
    nearest = find_nearest_stations(commune_lat, commune_lon, stations_df, n=n_stations, max_dist_km=max_dist_km)
    if nearest.empty:
        return {"error": "Aucune station meteo dans le rayon specifie."}
    station_ids = nearest["station_id"].tolist()
    results = compute_frost_days(meteo_df, station_ids, date_start_ts, date_end_ts)
    results["commune"] = commune_name
    results["dept"] = dept_code
    results["date_start"] = date_start
    results["date_end"] = date_end
    results["commune_lat"] = commune_lat
    results["commune_lon"] = commune_lon
    results["nearest_stations"] = nearest
    if not results.get("error"):
        results["monthly_summary"] = get_monthly_summary(results["frost_dates"], year_start, year_end)
        results["yearly_summary"] = get_yearly_summary(results["frost_dates"])
    return results
