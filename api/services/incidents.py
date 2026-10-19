"""Consultation des incidents et transitions de statut."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.models import Incident

TRANSITIONS_AUTORISEES = frozenset(
    {
        ("ouvert", "en_cours"),
        ("ouvert", "resolu"),
        ("en_cours", "resolu"),
    }
)


class TransitionRefusee(Exception):
    """Le passage demandé n'est pas une transition autorisée."""


def transition_autorisee(statut_actuel: str, nouveau_statut: str) -> bool:
    """RG7. Indique si le passage de statut est permis.

    Entrée : statut actuel et statut demandé.
    Fait : autorise ouvert vers en_cours, ouvert vers resolu, en_cours vers resolu.
    Retour : True si le couple est dans TRANSITIONS_AUTORISEES.
    """
    return (statut_actuel, nouveau_statut) in TRANSITIONS_AUTORISEES


def lister(
    session: Session,
    statut: str | None,
    page: int,
    taille_page: int,
) -> tuple[int, list[Incident]]:
    """Incidents paginés, filtrés par statut.

    Entrée : session, statut optionnel, page à partir de 1, taille de page.
    Fait : filtre égal au statut. Tri par date_signalement décroissante, puis incident_id.
    Retour : total filtré et la page d'incidents.
    """
    filtre = select(Incident)
    compte = select(func.count()).select_from(Incident)
    if statut:
        filtre = filtre.where(Incident.statut == statut)
        compte = compte.where(Incident.statut == statut)
    total = int(session.scalar(compte) or 0)
    lignes = session.scalars(
        filtre.order_by(Incident.date_signalement.desc(), Incident.incident_id.desc())
        .offset((page - 1) * taille_page)
        .limit(taille_page)
    ).all()
    return total, list(lignes)


def changer_statut(session: Session, incident_id: str, nouveau_statut: str) -> Incident | None:
    """Applique une transition et enregistre.

    Entrée : session, identifiant, nouveau statut (en_cours ou resolu).
    Fait : identifiant inconnu renvoyé tel quel. Transition refusée : lève TransitionRefusee. Le passage à resolu date la résolution si elle est vide.
    Retour : l'incident à jour, ou None si l'identifiant n'existe pas.
    """
    incident = session.get(Incident, incident_id)
    if incident is None:
        return None
    if not transition_autorisee(incident.statut, nouveau_statut):
        raise TransitionRefusee
    incident.statut = nouveau_statut
    if nouveau_statut == "resolu" and incident.date_resolution is None:
        incident.date_resolution = datetime.now().replace(microsecond=0)
    session.commit()
    session.refresh(incident)
    return incident
