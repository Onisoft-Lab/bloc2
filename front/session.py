"""Session Streamlit partagée par les écrans."""

import streamlit as st

_CLES = ("access_token", "role", "username")


def est_connecte() -> bool:
    return bool(st.session_state.get("access_token"))


def afficher_session(*, revenir_accueil: bool) -> None:
    if not est_connecte():
        return
    st.sidebar.markdown(f"**Connecté :** {st.session_state['username']}")
    st.sidebar.markdown(f"**Rôle :** {st.session_state['role']}")
    if st.sidebar.button("Se déconnecter", key="deconnexion_sidebar"):
        deconnecter()
        if revenir_accueil:
            st.switch_page("app.py")
        st.rerun()


def deconnecter() -> None:
    for cle in _CLES:
        st.session_state.pop(cle, None)


def exiger_connexion() -> None:
    afficher_session(revenir_accueil=True)
    if est_connecte():
        return
    st.info("Veuillez vous connecter")
    st.page_link("app.py", label="Page de connexion")
    st.stop()
