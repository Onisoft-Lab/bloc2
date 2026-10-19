"""Routes des incidents."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import IncidentLecture, MajStatut, PageIncidents
from api.securite import exiger_exploitant, utilisateur_courant
from api.services.incidents import TransitionRefusee, changer_statut, lister

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=PageIncidents)
def lire_incidents(
    statut: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    taille_page: int = Query(default=20, ge=1, le=100),
    _utilisateur: dict = Depends(utilisateur_courant),
    session: Session = Depends(get_db),
) -> PageIncidents:
    """GET /incidents. Jeton requis, les deux rôles. Tri par date de signalement décroissante."""
    statut_filtre = statut.strip() if statut else None
    total, lignes = lister(session, statut_filtre or None, page, taille_page)
    return PageIncidents(
        total=total,
        page=page,
        taille_page=taille_page,
        resultats=[IncidentLecture.model_validate(ligne) for ligne in lignes],
    )


@router.put("/incidents/{incident_id}/statut", response_model=IncidentLecture)
def modifier_statut(
    incident_id: str,
    corps: MajStatut,
    _exploitant: dict = Depends(exiger_exploitant),
    session: Session = Depends(get_db),
) -> IncidentLecture:
    """PUT /incidents/{id}/statut, réservé à l'exploitant.

    Entrée : identifiant et corps {statut: en_cours ou resolu}.
    Fait : exiger_exploitant répond 403 avant le corps. Transition refusée : 422. Identifiant inconnu : 404.
    Retour : l'incident mis à jour.
    """
    try:
        incident = changer_statut(session, incident_id, corps.statut)
    except TransitionRefusee:
        raise HTTPException(status_code=422, detail="Transition de statut non autorisee") from None
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident introuvable")
    return IncidentLecture.model_validate(incident)
