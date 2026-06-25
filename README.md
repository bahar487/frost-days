# ❄️ Frost Days — Calculateur de jours de gel

Projet Python avancé — Ynov Campus Marseille  
Données : Météo-France via [data.gouv.fr](https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes)

---

## 📌 Objectif

Calculer le nombre de **jours de gel** (température minimale ≤ 0 °C) pour une commune, un département et une plage de dates données.

**Outputs produits :**
- Nombre total de jours de gel sur la période
- Nombre moyen de jours de gel par année
- Fréquence de gel par jour de l'année (valeur absolue + relative)

---

## 🗂️ Structure du projet

```
frost_days/
├── app.py                   # Interface Streamlit
├── requirements.txt
├── README.md
├── src/
│   ├── data_loader.py       # Téléchargement & cache des données
│   ├── station_finder.py    # Haversine — stations les plus proches
│   ├── frost_engine.py      # Calcul des jours de gel
│   └── pipeline.py          # Orchestrateur principal
└── notebooks/
    └── analyse_exploratoire.ipynb  # Stats descriptives & QA
```

---

## ⚙️ Installation

```bash
git clone <url_du_repo>
cd frost_days
pip install -r requirements.txt
```

---

## 🚀 Lancement

### Interface graphique (Streamlit)

```bash
streamlit run app.py
```

### Ligne de commande

```bash
cd src
python pipeline.py
```

### Notebook

```bash
jupyter notebook notebooks/analyse_exploratoire.ipynb
```

---

## 📊 Sources de données

| Donnée | URL |
|--------|-----|
| Données météo quotidiennes | `https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/BASE/QUOT/` |
| Stations météo (postes synoptiques) | `https://object.files.data.gouv.fr/meteofrance/data/synchro_ftp/BASE/QUOT/poste_synop_0.csv` |
| Communes (coordonnées GPS) | `https://www.data.gouv.fr/fr/datasets/communes-et-villes-de-france-en-csv-excel-json-parquet-et-feather/` |

---

## 🧮 Méthodologie

### Définition d'un jour de gel
Un jour est dit **gelé** si la température minimale (`TN`) est ≤ 0 °C sur au moins une station valide.

### Sélection des stations
- Les **n stations les plus proches** de la commune sont identifiées par la **formule de Haversine** (distance à vol d'oiseau).
- Une station est **exclue** si elle présente plus de **35 %** de valeurs manquantes sur la période demandée.

### Statistiques par jour de l'année
- Le **29 février** est exclu (non pertinent statistiquement).
- Pour chaque jour (ex. 31 mars) : nombre d'années où ce jour a été un jour de gel + pourcentage.

### Volume des données
Les fichiers CSV Météo-France couvrent 1950–2023 par département.  
Les données sont **mises en cache en Parquet** après le premier téléchargement pour des performances optimales.

---

## 🌐 Interface graphique

L'interface Streamlit permet de :
- Saisir une commune, un département, une plage de dates
- Configurer le nombre de stations et le rayon de recherche
- Visualiser les résultats sous forme de graphiques interactifs (Plotly) :
  - Jours de gel par année
  - Jours de gel moyens par mois
  - Fréquence de gel par jour de l'année (absolu + relatif)
  - Carte des stations météo utilisées

---

## 🔧 Bonnes pratiques

- Code versionné sous **Git** (repo public)
- Séparation claire : chargement / calcul / interface
- Cache Parquet pour éviter les téléchargements répétés
- Gestion des valeurs manquantes (communes sans GPS, stations dégradées)
- Notebook de vérification de la qualité des données

---

## 👤 Auteur

Ali — Bachelor 3 Data & AI, Ynov Campus Marseille
