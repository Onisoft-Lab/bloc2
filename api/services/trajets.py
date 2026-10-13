"""Consultation des trajets."""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from api.models import Trajet


def lister(
    session: Session,
    date_debut: date | None,
    date_fin: date | None,
    station: str | None,
    page: int,
    taille_page: int,
) -> tuple[int, list[Trajet]]:
    filtre = select(Trajet)
    compte = select(func.count()).select_from(Trajet)
    jour = func.date(Trajet.depart_horodatage)
    conditions = []
    if date_debut is not None:
        conditions.append(jour >= date_debut)
    if date_fin is not None:
        conditions.append(jour <= date_fin)
    if station:
        conditions.append(or_(Trajet.station_depart == station, Trajet.station_arrivee == station))
    if conditions:
        filtre = filtre.where(*conditions)
        compte = compte.where(*conditions)
    total = int(session.scalar(compte) or 0)
    lignes = session.scalars(
        filtre.order_by(Trajet.depart_horodatage, Trajet.trajet_id)
        .offset((page - 1) * taille_page)
        .limit(taille_page)
    ).all()
    return total, list(lignes)
