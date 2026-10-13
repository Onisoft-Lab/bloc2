"""Les indicateurs restituent les agrégats SQL, pas un recalcul Python des lignes."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text

from api.services.indicateurs import activite_par_jour, incidents_par_statut, stations_actives


def test_activite_par_jour_alignee_sur_la_requete_sql(session):
    debut = date(2026, 8, 24)
    fin = date(2026, 8, 30)
    donnees = activite_par_jour(session, debut, fin)
    lignes = session.execute(
        text(
            """
            SELECT depart_horodatage::date AS jour, count(*) AS nb_trajets
            FROM trajet
            WHERE depart_horodatage::date BETWEEN :debut AND :fin
            GROUP BY jour
            ORDER BY jour
            """
        ),
        {"debut": debut, "fin": fin},
    ).all()
    assert [(ligne["jour"], ligne["nb_trajets"]) for ligne in donnees] == [
        (jour, nb) for jour, nb in lignes
    ]


def test_activite_sans_borne_couvre_tous_les_jours_presents(session):
    donnees = activite_par_jour(session, None, None)
    jours_sql = session.scalar(text("SELECT count(DISTINCT depart_horodatage::date) FROM trajet"))
    assert len(donnees) == jours_sql
    assert [ligne["jour"] for ligne in donnees] == sorted(ligne["jour"] for ligne in donnees)


def test_stations_actives_ordonnent_les_mouvements_et_ignorent_les_arrivees_inconnues(session):
    donnees = stations_actives(session, 10)
    assert len(donnees) == 10
    totaux = [ligne["nb_departs"] + ligne["nb_arrivees"] for ligne in donnees]
    assert totaux == sorted(totaux, reverse=True)
    for gauche, droite in zip(donnees, donnees[1:]):
        if gauche["nb_departs"] + gauche["nb_arrivees"] == droite["nb_departs"] + droite["nb_arrivees"]:
            assert gauche["station_id"] < droite["station_id"]

    toutes = stations_actives(session, 120)
    assert sum(ligne["nb_departs"] for ligne in toutes) == session.scalar(text("SELECT count(*) FROM trajet"))
    assert sum(ligne["nb_arrivees"] for ligne in toutes) == session.scalar(
        text("SELECT count(*) FROM trajet WHERE station_arrivee IS NOT NULL")
    )


def test_incidents_par_statut_et_delai_moyen(session):
    resultat = incidents_par_statut(session)
    comptes = {
        statut: nombre
        for statut, nombre in session.execute(text("SELECT statut, count(*) FROM incident GROUP BY statut"))
    }
    assert {ligne["statut"]: ligne["nb_incidents"] for ligne in resultat["donnees"]} == comptes
    moyenne = session.scalar(
        text(
            """
            SELECT avg(extract(epoch FROM (date_resolution - date_signalement)) / 3600)
            FROM incident
            WHERE statut = 'resolu' AND date_resolution IS NOT NULL
            """
        )
    )
    attendu = float(Decimal(str(moyenne)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    assert resultat["delai_moyen_resolution_heures"] == attendu
