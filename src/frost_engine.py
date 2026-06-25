"""
frost_engine.py
Calcul du nombre de jours de gel à partir des données météo filtrées.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict

MISSING_THRESHOLD = 0.35  # On exclut une station si > 35% de valeurs manquantes


def filter_valid_stations(
    meteo_df: pd.DataFrame,
    station_ids: list,
    date_start: pd.Timestamp,
    date_end: pd.Timestamp,
) -> list:
    """
    Filtre les stations ayant trop de valeurs manquantes sur la période.
    Une station est exclue si elle a plus de MISSING_THRESHOLD de NaN sur TN.
    """
    total_days = (date_end - date_start).days + 1
    valid = []

    for sid in station_ids:
        sub = meteo_df[
            (meteo_df["station_id"] == sid)
            & (meteo_df["date"] >= date_start)
            & (meteo_df["date"] <= date_end)
        ]
        if sub.empty:
            continue
        missing_rate = sub["tn"].isna().sum() / max(len(sub), 1)
        if missing_rate <= MISSING_THRESHOLD:
            valid.append(sid)

    return valid


def compute_frost_days(
    meteo_df: pd.DataFrame,
    station_ids: list,
    date_start: pd.Timestamp,
    date_end: pd.Timestamp,
) -> Dict:
    """
    Calcule les statistiques de jours de gel pour la liste de stations et la période donnée.

    Retourne un dictionnaire avec :
      - total_frost_days      : int
      - avg_frost_days_per_year : float
      - by_day_of_year        : DataFrame (month, day, frost_count, total_years, frost_pct)
      - frost_dates           : Series (dates où gel détecté)
      - n_valid_stations      : int
    """
    valid_stations = filter_valid_stations(meteo_df, station_ids, date_start, date_end)

    if not valid_stations:
        return {
            "total_frost_days": 0,
            "avg_frost_days_per_year": 0.0,
            "by_day_of_year": pd.DataFrame(),
            "frost_dates": pd.Series(dtype="datetime64[ns]"),
            "n_valid_stations": 0,
            "warning": "Aucune station valide trouvée pour cette commune et cette période.",
        }

    # Filtrer sur la période et les stations valides
    mask = (
        meteo_df["station_id"].isin(valid_stations)
        & (meteo_df["date"] >= date_start)
        & (meteo_df["date"] <= date_end)
    )
    df = meteo_df[mask].copy()

    # Gel = jour où TN <= 0°C sur AU MOINS une station
    df["is_frost"] = df["tn"] <= 0.0

    # Agrégation par date : un jour est un jour de gel si au moins une station le signale
    daily = (
        df.groupby("date")["is_frost"]
        .any()
        .reset_index()
        .rename(columns={"is_frost": "frost"})
    )

    # --- Indicateurs globaux ---
    total_frost_days = int(daily["frost"].sum())

    n_years = (date_end.year - date_start.year) + 1
    avg_frost_days_per_year = round(total_frost_days / n_years, 2) if n_years > 0 else 0.0

    # --- Statistiques par jour de l'année ---
    daily["month"] = daily["date"].dt.month
    daily["day"]   = daily["date"].dt.day
    daily["year"]  = daily["date"].dt.year

    # Exclure le 29 février (statistiques non pertinentes)
    daily = daily[~((daily["month"] == 2) & (daily["day"] == 29))]

    by_day = (
        daily.groupby(["month", "day"])
        .agg(
            frost_count=("frost", "sum"),
            observed_years=("year", "nunique"),
        )
        .reset_index()
    )

    # Calcul du pourcentage
    total_years = n_years
    by_day["total_years"] = total_years
    by_day["frost_pct"] = (by_day["frost_count"] / by_day["observed_years"] * 100).round(1)

    # Dates de gel
    frost_dates = daily[daily["frost"]]["date"].sort_values().reset_index(drop=True)

    return {
        "total_frost_days": total_frost_days,
        "avg_frost_days_per_year": avg_frost_days_per_year,
        "by_day_of_year": by_day,
        "frost_dates": frost_dates,
        "n_valid_stations": len(valid_stations),
        "valid_station_ids": valid_stations,
        "warning": None,
    }


def get_monthly_summary(frost_dates: pd.Series, year_start: int, year_end: int) -> pd.DataFrame:
    """Résumé mensuel : nombre de jours de gel par mois (moyenné sur les années)."""
    if frost_dates.empty:
        return pd.DataFrame(columns=["month", "avg_frost_days"])

    df = pd.DataFrame({"date": frost_dates})
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month

    monthly = df.groupby(["year", "month"]).size().reset_index(name="frost_days")
    avg = monthly.groupby("month")["frost_days"].mean().reset_index()
    avg.columns = ["month", "avg_frost_days"]
    avg["avg_frost_days"] = avg["avg_frost_days"].round(2)
    return avg


def get_yearly_summary(frost_dates: pd.Series) -> pd.DataFrame:
    """Nombre de jours de gel par année."""
    if frost_dates.empty:
        return pd.DataFrame(columns=["year", "frost_days"])
    df = pd.DataFrame({"date": frost_dates})
    df["year"] = df["date"].dt.year
    yearly = df.groupby("year").size().reset_index(name="frost_days")
    return yearly
