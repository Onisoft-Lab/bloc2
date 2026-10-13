"""Routes des trajets."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import PageTrajets, TrajetLecture
from api.securite import utilisateur_courant
from api.services.trajets import lister

router = APIRouter(tags=["trajets"])


@router.get("/trajets", response_model=PageTrajets)
def lire_trajets(
    date_debut: date | None = Query(default=None),
    date_fin: date | None = Query(default=None),
    station: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> PageTrajets:
    station_filtree = station.strip() if station else None
    total, lignes = lister(session, date_debut, date_fin, station_filtree or None, page, taille_page)
    return PageTrajets(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=[TrajetLecture.model_validate(ligne) for ligne in lignes],
    )
