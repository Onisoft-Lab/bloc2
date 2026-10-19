"""Écran des stations : filtre par commune et pagination."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from affichage import afficher_tableau
from api_client import ErreurApi, obtenir
from session import exiger_connexion

st.set_page_config(page_title="Stations - VéloVille", layout="wide")
exiger_connexion()

st.header("Stations")

COLONNES = {
    "station_id": "Identifiant",
    "nom": "Nom",
    "commune": "Commune",
    "capacite": "Capacité",
    "date_mise_en_service": "Mise en service",
}


@st.cache_data(ttl=3600)
def lister_communes(jeton: str) -> list[str]:
    """Communes distinctes, mises en cache une heure.

    Entrée : jeton Bearer. La clé de cache inclut le jeton.
    Fait : pagine GET /stations par 100 et déduplique les communes.
    Retour : liste triée. st.cache_data(ttl=3600).
    """
    communes: set[str] = set()
    page = 1
    while True:
        enveloppe = obtenir("/stations", jeton, params={"page": page, "taille_page": 100})
        for station in enveloppe["resultats"]:
            communes.add(station["commune"])
        if not enveloppe["resultats"] or page * 100 >= enveloppe["total"]:
            break
        page += 1
    return sorted(communes)


jeton = st.session_state["access_token"]
try:
    communes = lister_communes(jeton)
except ErreurApi as erreur:
    lister_communes.clear()
    st.error(str(erreur))
    st.stop()

colonne_commune, colonne_taille = st.columns(2)
commune = colonne_commune.selectbox("Commune", ["Toutes", *communes])
taille = colonne_taille.selectbox("Taille de page", [10, 20, 50], index=1)

if (
    st.session_state.get("memo_commune_stations") != commune
    or st.session_state.get("memo_taille_stations") != taille
):
    st.session_state["memo_commune_stations"] = commune
    st.session_state["memo_taille_stations"] = taille
    st.session_state["page_stations"] = 1

page = st.number_input("Page", min_value=1, step=1, key="page_stations")
parametres = {"page": int(page), "taille_page": int(taille)}
if commune != "Toutes":
    parametres["commune"] = commune

try:
    with st.spinner("Chargement..."):
        enveloppe = obtenir("/stations", jeton, params=parametres)
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

total = enveloppe["total"]
nb_pages = max(1, math.ceil(total / int(taille)))
st.write(f"{total} stations au total")
st.write(f"Page {int(page)} sur {nb_pages}")

if not enveloppe["resultats"]:
    st.info("Aucun résultat pour ces critères.")
else:
    afficher_tableau(enveloppe["resultats"], COLONNES)

colonne_prec, colonne_suiv = st.columns(2)
if colonne_prec.button("Page précédente", disabled=int(page) <= 1):
    st.session_state["page_stations"] = int(page) - 1
    st.rerun()
if colonne_suiv.button("Page suivante", disabled=int(page) >= nb_pages):
    st.session_state["page_stations"] = int(page) + 1
    st.rerun()
