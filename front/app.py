"""Écran de connexion VéloVille.

Lancement : streamlit run front/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from api_client import ErreurApi, connecter
from session import afficher_session, deconnecter, est_connecte

st.set_page_config(page_title="VéloVille - Connexion", layout="wide")
afficher_session(revenir_accueil=False)

st.title("VéloVille - Plateforme de restitution")
st.header("Connexion")

if est_connecte():
    st.success(
        f"Connecté en tant que {st.session_state['username']} "
        f"(rôle : {st.session_state['role']})."
    )
    st.write("Utilisez le menu latéral pour accéder aux écrans.")
    if st.button("Se déconnecter", key="deconnexion_accueil"):
        deconnecter()
        st.rerun()
else:
    with st.form("connexion"):
        identifiant = st.text_input("Identifiant")
        mot_de_passe = st.text_input("Mot de passe", type="password")
        soumis = st.form_submit_button("Se connecter")
    if soumis:
        with st.spinner("Chargement..."):
            try:
                reponse = connecter(identifiant, mot_de_passe)
            except ErreurApi as erreur:
                st.error(str(erreur))
            else:
                st.session_state["access_token"] = reponse["access_token"]
                st.session_state["role"] = reponse["role"]
                st.session_state["username"] = identifiant
                st.rerun()
