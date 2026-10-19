"""Routes des stations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import PageStations, StationLecture
from api.securite import utilisateur_courant
from api.services.stations import lister, obtenir

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=PageStations)
def lire_stations(
    commune: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> PageStations:
    """GET /stations. Jeton requis. Page ou taille hors bornes : 422 avant l'appel."""
    commune_filtree = commune.strip() if commune else None
    total, lignes = lister(session, commune_filtree or None, page, taille_page)
    return PageStations(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=[StationLecture.model_validate(ligne) for ligne in lignes],
    )


@router.get("/stations/{station_id}", response_model=StationLecture)
def lire_station(
    station_id: str,
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> StationLecture:
    """GET /stations/{id}. Jeton requis. Inconnue : 404 « Station introuvable »."""
    station = obtenir(session, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="Station introuvable")
    return StationLecture.model_validate(station)
