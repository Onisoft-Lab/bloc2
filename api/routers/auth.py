"""Connexion et émission du jeton."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import DemandeConnexion, Jeton
from api.securite import authentifier, emettre_jeton

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=Jeton)
def login(corps: DemandeConnexion, session: Session = Depends(get_db)) -> Jeton:
    """POST /auth/login. Échec : 401 « Identifiants invalides », sans dire si le compte existe."""
    utilisateur = authentifier(session, corps.username, corps.password)
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return Jeton(access_token=emettre_jeton(utilisateur.username, utilisateur.role), role=utilisateur.role)
