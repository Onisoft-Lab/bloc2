"""Authentification JWT et contrôle des rôles."""

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import Utilisateur

_BEARER = HTTPBearer(auto_error=False)
_ROLES = frozenset({"exploitant", "direction"})
_DETAIL_JETON = "Jeton absent, invalide ou expire"


@lru_cache(maxsize=1)
def _empreinte_fictive() -> bytes:
    """Rend la connexion d'un identifiant inconnu aussi coûteuse qu'un échec de mot de passe."""
    return bcrypt.hashpw(b"compte-inconnu", bcrypt.gensalt(rounds=12))


def mot_de_passe_valide(mot_de_passe: str, empreinte: str | bytes) -> bool:
    try:
        attendue = empreinte.encode("utf-8") if isinstance(empreinte, str) else empreinte
        return bcrypt.checkpw(mot_de_passe.encode("utf-8"), attendue)
    except ValueError:
        return False


def authentifier(session: Session, username: str, password: str) -> Utilisateur | None:
    utilisateur = session.scalar(select(Utilisateur).where(Utilisateur.username == username))
    empreinte = utilisateur.mot_de_passe_hash if utilisateur is not None else _empreinte_fictive()
    if not mot_de_passe_valide(password, empreinte) or utilisateur is None:
        return None
    return utilisateur


def emettre_jeton(username: str, role: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(minutes=_duree_minutes())
    jeton = jwt.encode(
        {"sub": username, "role": role, "exp": expiration},
        _secret(),
        algorithm="HS256",
    )
    if isinstance(jeton, bytes):
        return jeton.decode("utf-8")
    return jeton


def utilisateur_courant(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail=_DETAIL_JETON)
    try:
        charge = jwt.decode(
            credentials.credentials,
            _secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except PyJWTError:
        raise HTTPException(status_code=401, detail=_DETAIL_JETON) from None
    identifiant = charge.get("sub")
    role = charge.get("role")
    if not isinstance(identifiant, str) or role not in _ROLES:
        raise HTTPException(status_code=401, detail=_DETAIL_JETON)
    return {"username": identifiant, "role": role}


def exiger_exploitant(utilisateur: dict[str, str] = Depends(utilisateur_courant)) -> dict[str, str]:
    if utilisateur["role"] != "exploitant":
        raise HTTPException(status_code=403, detail="Acces reserve au role exploitant")
    return utilisateur


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET est absent de l'environnement")
    return secret


def _duree_minutes() -> int:
    brut = os.environ.get("JWT_EXPIRATION_MINUTES", "60").strip()
    try:
        duree = int(brut)
    except ValueError as erreur:
        raise RuntimeError("JWT_EXPIRATION_MINUTES n'est pas un entier") from erreur
    if duree <= 0:
        raise RuntimeError("JWT_EXPIRATION_MINUTES doit être strictement positif")
    return duree
