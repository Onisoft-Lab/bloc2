"""Écran des incidents : filtre par statut et changement de statut."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from affichage import afficher_tableau, formater_horodatage
from api_client import ErreurApi, modifier_statut, obtenir
from session import exiger_connexion

st.set_page_config(page_title="Incidents - VéloVille", layout="wide")
exiger_connexion()

st.header("Incidents")

COLONNES = {
    "incident_id": "Identifiant",
    "date_signalement": "Signalé le",
    "cible": "Cible",
    "velo_id": "Vélo",
    "station_id": "Station",
    "type_incident": "Type",
    "statut": "Statut",
    "date_resolution": "Résolu le",
    "technicien": "Technicien",
}

jeton = st.session_state["access_token"]
colonne_statut, colonne_taille = st.columns(2)
statut = colonne_statut.selectbox("Statut", ["Tous", "ouvert", "en_cours", "resolu"])
taille = colonne_taille.selectbox("Taille de page", [10, 20, 50], index=1)

if (
    st.session_state.get("memo_statut_incidents") != statut
    or st.session_state.get("memo_taille_incidents") != taille
):
    st.session_state["memo_statut_incidents"] = statut
    st.session_state["memo_taille_incidents"] = taille
    st.session_state["page_incidents"] = 1

page = st.number_input("Page", min_value=1, step=1, key="page_incidents")
parametres = {"page": int(page), "taille_page": int(taille)}
if statut != "Tous":
    parametres["statut"] = statut

try:
    with st.spinner("Chargement..."):
        enveloppe = obtenir("/incidents", jeton, params=parametres)
except ErreurApi as erreur:
    st.error(str(erreur))
    st.stop()

total = enveloppe["total"]
nb_pages = max(1, math.ceil(total / int(taille)) if total else 1)
st.write(f"{total} incidents au total")
st.write(f"Page {int(page)} sur {nb_pages}")

if not enveloppe["resultats"]:
    st.info("Aucun résultat pour ces critères.")
else:
    lignes = []
    for incident in enveloppe["resultats"]:
        copie = dict(incident)
        copie["date_signalement"] = formater_horodatage(incident["date_signalement"])
        copie["date_resolution"] = formater_horodatage(incident.get("date_resolution"))
        lignes.append(copie)
    afficher_tableau(lignes, COLONNES)

colonne_prec, colonne_suiv = st.columns(2)
if colonne_prec.button("Page précédente", disabled=int(page) <= 1):
    st.session_state["page_incidents"] = int(page) - 1
    st.rerun()
if colonne_suiv.button("Page suivante", disabled=int(page) >= nb_pages):
    st.session_state["page_incidents"] = int(page) + 1
    st.rerun()

message = st.session_state.pop("flash_incident", None)
if message:
    st.success(message)

if st.session_state["role"] != "exploitant":
    st.info("La modification des incidents est réservée aux exploitants.")
    st.stop()

st.subheader("Changer le statut d'un incident")
if not enveloppe["resultats"]:
    st.stop()

with st.form("changer_statut"):
    incident_id = st.selectbox(
        "Incident",
        [ligne["incident_id"] for ligne in enveloppe["resultats"]],
    )
    nouveau = st.selectbox("Nouveau statut", ["en_cours", "resolu"])
    soumis = st.form_submit_button("Appliquer")

if soumis:
    try:
        with st.spinner("Chargement..."):
            modifier_statut(jeton, incident_id, nouveau)
    except ErreurApi as erreur:
        st.error(str(erreur))
    else:
        st.session_state["flash_incident"] = (
            f"Statut de l'incident {incident_id} mis à jour : {nouveau}."
        )
        st.rerun()
