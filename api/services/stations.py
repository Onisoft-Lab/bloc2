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
    """Stations paginées, filtrées par commune.

    Entrée : session, commune optionnelle (égalité stricte), page à partir de 1, taille de page.
    Fait : tri par station_id. Une page au-delà du total est vide. Le total reste le compte filtré.
    Retour : total filtré et la page de stations.
    """
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
    """Lit une station par sa clé.

    Entrée : session et station_id.
    Fait : lecture par clé primaire.
    Retour : la station, ou None si elle n'existe pas.
    """
    return session.get(Station, station_id)
