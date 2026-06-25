"""
app.py
Interface Streamlit — Frost Days Calculator
Lancer : streamlit run app.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from pipeline import run_frost_analysis

# ─── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Frost Days 🌡️",
    page_icon="❄️",
    layout="wide",
)

# ─── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1f3c 0%, #2d3561 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .metric-value { font-size: 2.4rem; font-weight: 700; color: #7ec8e3; }
    .metric-label { font-size: 0.85rem; color: #aab4c8; margin-top: 4px; }
    .warn-box {
        background: #fff3cd; border-left: 4px solid #ffc107;
        padding: 0.75rem 1rem; border-radius: 6px; color: #856404;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/115px-Python-logo-notext.svg.png", width=50)
    st.title("❄️ Frost Days")
    st.caption("Données Météo-France • data.gouv.fr")
    st.divider()

    commune = st.text_input("🏙️ Commune", value="Grenoble", placeholder="ex: Grenoble")
    dept    = st.text_input("🗺️ Département", value="38", placeholder="ex: 38, 75, 13...")

    col_a, col_b = st.columns(2)
    with col_a:
        d_start = st.date_input("📅 Début", value=date(2014, 1, 1), min_value=date(1950, 1, 1), max_value=date(2023, 12, 31))
    with col_b:
        d_end   = st.date_input("📅 Fin",   value=date(2023, 12, 31), min_value=date(1950, 1, 1), max_value=date(2023, 12, 31))

    n_stations  = st.slider("Nb stations max", 1, 10, 5)
    max_dist_km = st.slider("Rayon max (km)",  10, 200, 100)

    run_btn = st.button("🔍 Calculer", type="primary", use_container_width=True)

    st.divider()
    st.caption("ℹ️ Les données sont mises en cache localement après le premier téléchargement.")

# ─── Main content ─────────────────────────────────────────────────────────────
st.title("❄️ Calculateur de Jours de Gel")
st.caption("Analyse des jours de gel à partir des données climatologiques Météo-France.")

if not run_btn:
    st.info("👈 Renseignez une commune et une période dans le panneau latéral, puis cliquez sur **Calculer**.")
    st.markdown("""
    ### Comment ça marche ?
    1. On localise votre commune grâce au fichier référentiel data.gouv.fr
    2. On identifie les stations météo les plus proches (formule de Haversine)
    3. On exclut les stations avec > 35 % de valeurs manquantes
    4. Un jour est considéré *gelé* si la température minimale ≤ 0 °C sur au moins une station
    5. On calcule les statistiques globales et par jour de l'année
    """)
    st.stop()

# ─── Run pipeline ─────────────────────────────────────────────────────────────
with st.spinner("Analyse en cours…"):
    results = run_frost_analysis(
        commune_name=commune,
        dept_code=dept,
        date_start=str(d_start),
        date_end=str(d_end),
        n_stations=n_stations,
        max_dist_km=max_dist_km,
    )

if "error" in results:
    st.error(f"❌ {results['error']}")
    st.stop()

if results.get("warning"):
    st.warning(results["warning"])

# ─── Métriques globales ───────────────────────────────────────────────────────
st.subheader(f"📊 {commune} ({dept}) — {d_start.year} → {d_end.year}")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{results['total_frost_days']}</div>
        <div class="metric-label">Jours de gel totaux</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{results['avg_frost_days_per_year']}</div>
        <div class="metric-label">Moy. jours de gel / an</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{results['n_valid_stations']}</div>
        <div class="metric-label">Stations valides utilisées</div>
    </div>""", unsafe_allow_html=True)
with c4:
    years = (d_end.year - d_start.year) + 1
    st.markdown(f"""<div class="metric-card">
        <div class="metric-value">{years}</div>
        <div class="metric-label">Années analysées</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ─── Graphiques ──────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📅 Par année", "📆 Par mois", "🗓️ Par jour de l'année", "📍 Stations"])

# Tab 1 – Par année
with tab1:
    yearly = results.get("yearly_summary", pd.DataFrame())
    if not yearly.empty:
        fig = px.bar(
            yearly, x="year", y="frost_days",
            title="Jours de gel par année",
            labels={"year": "Année", "frost_days": "Jours de gel"},
            color="frost_days",
            color_continuous_scale="Blues_r",
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données annuelles.")

# Tab 2 – Par mois
with tab2:
    monthly = results.get("monthly_summary", pd.DataFrame())
    if not monthly.empty:
        MONTH_NAMES = {1:"Jan", 2:"Fév", 3:"Mar", 4:"Avr", 5:"Mai", 6:"Juin",
                       7:"Juil", 8:"Août", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Déc"}
        monthly["month_name"] = monthly["month"].map(MONTH_NAMES)
        fig = px.bar(
            monthly, x="month_name", y="avg_frost_days",
            title="Moyenne jours de gel par mois",
            labels={"month_name": "Mois", "avg_frost_days": "Jours de gel (moy.)"},
            color="avg_frost_days",
            color_continuous_scale="Blues_r",
        )
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de données mensuelles.")

# Tab 3 – Par jour de l'année
with tab3:
    bday = results.get("by_day_of_year", pd.DataFrame())
    if not bday.empty:
        # Construire une date fictive pour l'axe X
        bday["date_label"] = pd.to_datetime(
            "2000-" + bday["month"].astype(str).str.zfill(2) + "-" + bday["day"].astype(str).str.zfill(2),
            errors="coerce"
        )
        bday = bday.dropna(subset=["date_label"]).sort_values("date_label")

        col_l, col_r = st.columns(2)
        with col_l:
            fig_abs = px.bar(
                bday, x="date_label", y="frost_count",
                title="Jours de gel par jour de l'année (valeur absolue)",
                labels={"date_label": "Jour", "frost_count": "Nb années avec gel"},
                color="frost_count",
                color_continuous_scale="Blues_r",
            )
            fig_abs.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_abs, use_container_width=True)

        with col_r:
            fig_pct = px.bar(
                bday, x="date_label", y="frost_pct",
                title="Fréquence de gel par jour de l'année (%)",
                labels={"date_label": "Jour", "frost_pct": "% années avec gel"},
                color="frost_pct",
                color_continuous_scale="RdBu_r",
            )
            fig_pct.update_layout(showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_pct, use_container_width=True)

        # Top 10 jours les plus gelés
        st.subheader("🏆 Top 10 jours les plus fréquemment gelés")
        MONTH_NAMES = {1:"Jan", 2:"Fév", 3:"Mar", 4:"Avr", 5:"Mai", 6:"Juin",
                       7:"Juil", 8:"Août", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Déc"}
        top10 = bday.sort_values("frost_pct", ascending=False).head(10).copy()
        top10["Jour"] = top10["day"].astype(str) + " " + top10["month"].map(MONTH_NAMES)
        top10 = top10.rename(columns={"frost_count": "Nb années avec gel", "frost_pct": "Fréquence (%)"})
        st.dataframe(
            top10[["Jour", "Nb années avec gel", "Fréquence (%)"]].reset_index(drop=True),
            use_container_width=True,
        )
    else:
        st.info("Pas de données par jour.")

# Tab 4 – Stations
with tab4:
    nearest = results.get("nearest_stations", pd.DataFrame())
    if not nearest.empty:
        st.subheader("📍 Stations météo utilisées")
        st.dataframe(
            nearest[["station_id", "lat", "lon", "distance_km"]].rename(
                columns={"station_id": "ID Station", "lat": "Latitude",
                         "lon": "Longitude", "distance_km": "Distance (km)"}
            ),
            use_container_width=True,
        )
        # Mini carte
        map_df = nearest.rename(columns={"lat": "latitude", "lon": "longitude"})
        commune_point = pd.DataFrame([{
            "latitude": results["commune_lat"],
            "longitude": results["commune_lon"],
            "station_id": f"📍 {commune}",
            "distance_km": 0.0,
        }])
        map_all = pd.concat([map_df, commune_point], ignore_index=True)
        st.map(map_all, latitude="latitude", longitude="longitude", zoom=8)
    else:
        st.info("Aucune station.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("Source : Météo-France / data.gouv.fr • Données climatologiques quotidiennes • Projet Frost Days")
