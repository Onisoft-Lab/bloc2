"""Routes des trois indicateurs."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import ReponseActivite, ReponseIncidentsStatut, ReponseStationsActives
from api.securite import utilisateur_courant
from api.services.indicateurs import activite_par_jour, incidents_par_statut, stations_actives

router = APIRouter(tags=["indicateurs"])


@router.get("/indicateurs/activite-par-jour", response_model=ReponseActivite)
def lire_activite(
    date_debut: date | None = Query(default=None),
    date_fin: date | None = Query(default=None),
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> dict:
    return {"donnees": activite_par_jour(session, date_debut, date_fin)}


@router.get("/indicateurs/stations-actives", response_model=ReponseStationsActives)
def lire_stations_actives(
    limite: int = Query(default=10, ge=1),
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> dict:
    return {"donnees": stations_actives(session, limite)}


@router.get("/indicateurs/incidents-par-statut", response_model=ReponseIncidentsStatut)
def lire_incidents_par_statut(
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> dict:
    return incidents_par_statut(session)
