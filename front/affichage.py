"""Mise en forme commune des tableaux."""

import streamlit as st


def afficher_tableau(lignes: list[dict], colonnes: dict[str, str]) -> None:
    visibles = [
        {libelle: _texte(ligne.get(cle)) for cle, libelle in colonnes.items()}
        for ligne in lignes
    ]
    st.dataframe(visibles, hide_index=True, width="stretch")


def formater_horodatage(valeur: str | None) -> str:
    if not valeur:
        return ""
    return valeur.replace("T", " ")[:16]


def _texte(valeur: object) -> str:
    if valeur is None:
        return ""
    return str(valeur)
