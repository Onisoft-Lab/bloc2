"""Consultation des stations."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Station


def lister(
    session: Session,
    commune: str | None,
    page: int,
    taille_page: int,
) -> tuple[int, list[Station]]:
    filtre = select(Station)
    compte = select(func.count()).select_from(Station)
    if commune:
        filtre = filtre.where(Station.commune == commune)
        compte = compte.where(Station.commune == commune)
    total = int(session.scalar(compte) or 0)
    lignes = session.scalars(
        filtre.order_by(Station.station_id).offset((page - 1) * taille_page).limit(taille_page)
    ).all()
    return total, list(lignes)


def obtenir(session: Session, station_id: str) -> Station | None:
    return session.get(Station, station_id)
