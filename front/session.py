"""Session Streamlit partagée par les écrans."""

import streamlit as st

_CLES = ("access_token", "role", "username")


def est_connecte() -> bool:
    """Indique si un jeton est en session.

    Entrée : st.session_state.
    Fait : teste la présence de access_token.
    Retour : True si l'utilisateur est connecté. Le jeton n'est jamais affiché.
    """
    return bool(st.session_state.get("access_token"))


def afficher_session(*, revenir_accueil: bool) -> None:
    """Affiche l'identifiant et le rôle dans la barre latérale.

    Entrée : revenir_accueil, vrai sur les pages, faux sur l'accueil.
    Fait : montre username et role. La déconnexion retire le jeton. Le jeton reste invisible.
    Retour : rien.
    """
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
    """Retire le jeton, le rôle et l'identifiant de la session.

    Entrée : aucune.
    Fait : retire access_token, role et username.
    Retour : rien.
    """
    for cle in _CLES:
        st.session_state.pop(cle, None)


def exiger_connexion() -> None:
    """Bloque une page si personne n'est connecté.

    Entrée : la session courante.
    Fait : affiche la barre. Sinon un message, un lien vers la connexion, puis stop.
    Retour : rien si la session est ouverte.
    """
    afficher_session(revenir_accueil=True)
    if est_connecte():
        return
    st.info("Veuillez vous connecter")
    st.page_link("app.py", label="Page de connexion")
    st.stop()
