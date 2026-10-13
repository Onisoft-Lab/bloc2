"""Contrats HTTP : santé, connexion, jeton et droits."""

from sqlalchemy import select, text

from api.models import Incident
from tests.conftest import mot_de_passe


def _auth(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def test_sante_sans_jeton(client):
    reponse = client.get("/sante")
    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "ok"}


def test_login_accepte_les_deux_roles(client):
    for username, role in (("exploitant01", "exploitant"), ("direction01", "direction")):
        reponse = client.post(
            "/auth/login",
            json={"username": username, "password": mot_de_passe()},
        )
        assert reponse.status_code == 200
        corps = reponse.json()
        assert corps["access_token"]
        assert corps["token_type"] == "bearer"
        assert corps["role"] == role


def test_login_refuse_sans_reveler_si_le_compte_existe(client):
    mauvais = client.post(
        "/auth/login",
        json={"username": "exploitant01", "password": "mauvais"},
    )
    inconnu = client.post(
        "/auth/login",
        json={"username": "inconnu", "password": mot_de_passe()},
    )
    assert mauvais.status_code == 401
    assert inconnu.status_code == 401
    assert mauvais.json() == {"detail": "Identifiants invalides"}
    assert inconnu.json() == mauvais.json()


def test_route_protegee_sans_jeton_ou_jeton_invalide(client, jeton_direction):
    assert client.get("/stations").status_code == 401
    assert client.get("/stations", headers={"Authorization": "Bearer jeton.invalide.xyz"}).status_code == 401
    modifie = jeton_direction[:-1] + ("a" if jeton_direction[-1] != "a" else "b")
    assert client.get("/stations", headers=_auth(modifie)).status_code == 401


def test_stations_paginees_et_filtre_lille(client, jeton_direction):
    entete = _auth(jeton_direction)
    page = client.get("/stations", params={"taille_page": 50, "page": 1}, headers=entete)
    assert page.status_code == 200
    corps = page.json()
    assert corps["total"] == 120
    assert corps["page"] == 1
    assert corps["taille_page"] == 50
    assert len(corps["resultats"]) == 50
    assert corps["resultats"][0]["station_id"] == "S001"
    assert corps["resultats"][0]["nom"] == "Lille - Gare"

    suivante = client.get("/stations", params={"taille_page": 50, "page": 3}, headers=entete)
    assert len(suivante.json()["resultats"]) == 20

    lille = client.get("/stations", params={"commune": "Lille", "taille_page": 100}, headers=entete)
    assert lille.json()["total"] == 46
    assert {ligne["commune"] for ligne in lille.json()["resultats"]} == {"Lille"}

    assert client.get("/stations", params={"page": 0}, headers=entete).status_code == 422
    assert client.get("/stations", params={"taille_page": 101}, headers=entete).status_code == 422


def test_trajets_et_incidents_filtres(client, jeton_direction):
    entete = _auth(jeton_direction)
    trajets = client.get(
        "/trajets",
        params={"date_debut": "2026-08-24", "date_fin": "2026-08-30", "station": "S001", "taille_page": 20},
        headers=entete,
    )
    assert trajets.status_code == 200
    assert trajets.json()["total"] >= 1
    assert trajets.json()["resultats"]

    incidents = client.get("/incidents", params={"statut": "ouvert", "taille_page": 5}, headers=entete)
    assert incidents.status_code == 200
    assert incidents.json()["total"] >= 1
    assert {ligne["statut"] for ligne in incidents.json()["resultats"]} == {"ouvert"}


def test_incident_introuvable(client, jeton_exploitant):
    reponse = client.put(
        "/incidents/I2026-9999/statut",
        json={"statut": "resolu"},
        headers=_auth(jeton_exploitant),
    )
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Incident introuvable"}


def test_station_introuvable(client, jeton_direction):
    entete = _auth(jeton_direction)
    assert client.get("/stations/S001", headers=entete).json()["nom"] == "Lille - Gare"
    introuvable = client.get("/stations/S999", headers=entete)
    assert introuvable.status_code == 404
    assert introuvable.json() == {"detail": "Station introuvable"}


def test_direction_ne_modifie_pas_un_incident_exploitant_oui_puis_restauration(
    client, jeton_direction, jeton_exploitant, session
):
    incident_id = session.scalar(
        select(Incident.incident_id).where(Incident.statut == "ouvert").order_by(Incident.incident_id).limit(1)
    )
    assert incident_id
    try:
        refus = client.put(
            f"/incidents/{incident_id}/statut",
            json={"statut": "en_cours"},
            headers=_auth(jeton_direction),
        )
        assert refus.status_code == 403
        assert refus.json() == {"detail": "Acces reserve au role exploitant"}
        session.expire_all()
        assert session.get(Incident, incident_id).statut == "ouvert"

        accepte = client.put(
            f"/incidents/{incident_id}/statut",
            json={"statut": "en_cours"},
            headers=_auth(jeton_exploitant),
        )
        assert accepte.status_code == 200
        assert accepte.json()["statut"] == "en_cours"

        interdit = client.put(
            f"/incidents/{incident_id}/statut",
            json={"statut": "en_cours"},
            headers=_auth(jeton_exploitant),
        )
        assert interdit.status_code == 422
        assert interdit.json() == {"detail": "Transition de statut non autorisee"}

        resolu = client.put(
            f"/incidents/{incident_id}/statut",
            json={"statut": "resolu"},
            headers=_auth(jeton_exploitant),
        )
        assert resolu.status_code == 200
        assert resolu.json()["statut"] == "resolu"
        assert resolu.json()["date_resolution"]
    finally:
        session.execute(
            text(
                "UPDATE incident SET statut = 'ouvert', date_resolution = NULL "
                "WHERE incident_id = :incident_id"
            ),
            {"incident_id": incident_id},
        )
        session.commit()
