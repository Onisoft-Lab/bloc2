"""Écran des trois indicateurs, restitution tabulaire."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from affichage import afficher_tableau
from api_client import ErreurApi, obtenir
from session import exiger_connexion

st.set_page_config(page_title="Indicateurs - VéloVille", layout="wide")
exiger_connexion()

st.header("Indicateurs")

DEFAUT = {"debut": date(2026, 8, 24), "fin": date(2026, 8, 30), "limite": 10}
if "criteres_indicateurs" not in st.session_state:
    st.session_state["criteres_indicateurs"] = DEFAUT

with st.form("filtres_indicateurs"):
    debut = st.date_input("Début de période", value=st.session_state["criteres_indicateurs"]["debut"])
    fin = st.date_input("Fin de période", value=st.session_state["criteres_indicateurs"]["fin"])
    limite = st.number_input(
        "Nombre de stations actives",
        min_value=1,
        max_value=50,
        value=int(st.session_state["criteres_indicateurs"]["limite"]),
    )
    soumis = st.form_submit_button("Actualiser")

params = st.session_state["criteres_indicateurs"]
if soumis:
    params = {"debut": debut, "fin": fin, "limite": int(limite)}
    st.session_state["criteres_indicateurs"] = params

if params["debut"] > params["fin"]:
    st.error("La date de début est postérieure à la date de fin.")
    st.stop()

jeton = st.session_state["access_token"]
try:
    with st.spinner("Chargement..."):
        activite = obtenir(
            "/indicateurs/activite-par-jour",
            jeton,
            params={"date_debut": params["debut"].isoformat(), "date_fin": params["fin"].isoformat()},
        )
        stations = obtenir(
            "/indicateurs/stations-actives",
            jeton,
            params={"limite": int(params["limite"])},
        )
        incidents = obtenir("/indicateurs/incidents-par-statut", jeton)
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

delai = incidents["delai_moyen_resolution_heures"]
colonne_trajets, colonne_stations, colonne_delai = st.columns(3)
colonne_trajets.metric("Trajets sur la période", sum(ligne["nb_trajets"] for ligne in activite["donnees"]))
colonne_stations.metric("Stations actives", len(stations["donnees"]))
colonne_delai.metric(
    "Délai moyen de résolution (h)",
    "n. d." if delai is None else f"{delai:.1f}".replace(".", ","),
)

st.subheader("Activité par jour")
if not activite["donnees"]:
    st.info("Aucun résultat pour ces critères.")
else:
    afficher_tableau(activite["donnees"], {"jour": "Jour", "nb_trajets": "Nombre de trajets"})

st.subheader("Stations les plus actives")
if not stations["donnees"]:
    st.info("Aucun résultat pour ces critères.")
else:
    lignes_stations = [
        {
            "station_id": ligne["station_id"],
            "nom": ligne["nom"],
            "nb_departs": ligne["nb_departs"],
            "nb_arrivees": ligne["nb_arrivees"],
            "total": ligne["nb_departs"] + ligne["nb_arrivees"],
        }
        for ligne in stations["donnees"]
    ]
    afficher_tableau(
        lignes_stations,
        {
            "station_id": "Identifiant",
            "nom": "Nom",
            "nb_departs": "Départs",
            "nb_arrivees": "Arrivées",
            "total": "Total",
        },
    )

st.subheader("Incidents par statut")
if not incidents["donnees"]:
    st.info("Aucun résultat pour ces critères.")
else:
    afficher_tableau(incidents["donnees"], {"statut": "Statut", "nb_incidents": "Nombre d'incidents"})
