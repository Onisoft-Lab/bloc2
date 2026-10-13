"""Client HTTP centralisé vers l'API VéloVille."""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parents[1]
load_dotenv(RACINE / ".env")

_MESSAGES = {
    "Identifiants invalides": "Identifiant ou mot de passe incorrect.",
    "Acces reserve au role exploitant": "Vous n'avez pas le droit de modifier un incident.",
    "Transition de statut non autorisee": "Transition de statut non autorisée.",
    "Incident introuvable": "Incident introuvable.",
    "Station introuvable": "Station introuvable.",
    "Jeton absent, invalide ou expire": "Session expirée ou jeton invalide.",
}


class ErreurApi(Exception):
    """Erreur levée lorsque l'API est injoignable ou répond en erreur."""

    def __init__(self, message: str, statut_http: int | None = None) -> None:
        super().__init__(message)
        self.statut_http = statut_http


def connecter(identifiant: str, mot_de_passe: str) -> dict:
    return appeler("POST", "/auth/login", json={"username": identifiant, "password": mot_de_passe})


def obtenir(chemin: str, jeton: str, params: dict | None = None) -> dict:
    return appeler("GET", chemin, jeton=jeton, params=params)


def modifier_statut(jeton: str, incident_id: str, statut: str) -> dict:
    return appeler("PUT", f"/incidents/{incident_id}/statut", jeton=jeton, json={"statut": statut})


def appeler(
    methode: str,
    chemin: str,
    jeton: str | None = None,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    entetes = {}
    if jeton:
        entetes["Authorization"] = f"Bearer {jeton}"
    try:
        reponse = requests.request(
            methode,
            f"{_url()}{chemin}",
            headers=entetes,
            params=params,
            json=json,
            timeout=_delai(),
        )
    except requests.RequestException:
        raise ErreurApi("L'API est injoignable. Vérifiez qu'elle est démarrée.") from None
    if reponse.status_code >= 400:
        raise ErreurApi(_message(reponse), reponse.status_code)
    try:
        return reponse.json()
    except ValueError:
        raise ErreurApi("L'API a renvoyé une réponse illisible.") from None


def _url() -> str:
    return os.environ.get("API_URL", "http://localhost:8000").rstrip("/")


def _delai() -> float:
    return float(os.environ.get("API_TIMEOUT_SECONDES", "5"))


def _message(reponse: requests.Response) -> str:
    try:
        corps = reponse.json()
    except ValueError:
        return "L'API a renvoyé une réponse illisible."
    detail = corps.get("detail") if isinstance(corps, dict) else None
    if isinstance(detail, str):
        return _MESSAGES.get(detail, detail)
    if reponse.status_code == 422:
        return "Les paramètres envoyés sont invalides."
    return "L'API a renvoyé une erreur."
