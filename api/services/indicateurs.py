"""Indicateurs calculés par agrégation SQL."""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Incident, Station, Trajet


def activite_par_jour(
    session: Session,
    date_debut: date | None,
    date_fin: date | None,
) -> list[dict]:
    jour = func.date(Trajet.depart_horodatage)
    requete = select(jour.label("jour"), func.count().label("nb_trajets"))
    if date_debut is not None:
        requete = requete.where(jour >= date_debut)
    if date_fin is not None:
        requete = requete.where(jour <= date_fin)
    requete = requete.group_by(jour).order_by(jour)
    lignes = []
    for valeur_jour, nombre in session.execute(requete):
        if isinstance(valeur_jour, datetime):
            valeur_jour = valeur_jour.date()
        lignes.append({"jour": valeur_jour, "nb_trajets": int(nombre)})
    return lignes


def stations_actives(session: Session, limite: int) -> list[dict]:
    departs = (
        select(Trajet.station_depart.label("station_id"), func.count().label("nb_departs"))
        .group_by(Trajet.station_depart)
        .subquery()
    )
    arrivees = (
        select(Trajet.station_arrivee.label("station_id"), func.count().label("nb_arrivees"))
        .where(Trajet.station_arrivee.is_not(None))
        .group_by(Trajet.station_arrivee)
        .subquery()
    )
    nb_departs = func.coalesce(departs.c.nb_departs, 0)
    nb_arrivees = func.coalesce(arrivees.c.nb_arrivees, 0)
    mouvements = nb_departs + nb_arrivees
    requete = (
        select(
            Station.station_id,
            Station.nom,
            nb_departs.label("nb_departs"),
            nb_arrivees.label("nb_arrivees"),
        )
        .outerjoin(departs, departs.c.station_id == Station.station_id)
        .outerjoin(arrivees, arrivees.c.station_id == Station.station_id)
        .where(mouvements > 0)
        .order_by(mouvements.desc(), Station.station_id.asc())
        .limit(limite)
    )
    return [
        {
            "station_id": station_id,
            "nom": nom,
            "nb_departs": int(nb_dep),
            "nb_arrivees": int(nb_arr),
        }
        for station_id, nom, nb_dep, nb_arr in session.execute(requete)
    ]


def incidents_par_statut(session: Session) -> dict:
    comptes = session.execute(
        select(Incident.statut, func.count().label("nb_incidents"))
        .group_by(Incident.statut)
        .order_by(Incident.statut)
    ).all()
    secondes = func.extract("epoch", Incident.date_resolution - Incident.date_signalement)
    moyenne = session.scalar(
        select(func.avg(secondes / 3600.0)).where(
            Incident.statut == "resolu",
            Incident.date_resolution.is_not(None),
        )
    )
    return {
        "donnees": [{"statut": statut, "nb_incidents": int(nombre)} for statut, nombre in comptes],
        "delai_moyen_resolution_heures": _arrondir_heure(moyenne),
    }


def _arrondir_heure(moyenne: object) -> float | None:
    if moyenne is None:
        return None
    arrondi = Decimal(str(moyenne)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return float(arrondi)
