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
    """Rend un identifiant inconnu aussi coûteux qu'un mauvais mot de passe.

    Entrée : aucune. Le résultat est mis en cache.
    Fait : bcrypt de « compte-inconnu », 12 rounds, calculé une fois.
    Retour : empreinte utilisée quand le compte n'existe pas.
    """
    return bcrypt.hashpw(b"compte-inconnu", bcrypt.gensalt(rounds=12))


def mot_de_passe_valide(mot_de_passe: str, empreinte: str | bytes) -> bool:
    """Compare un mot de passe à une empreinte bcrypt.

    Entrée : mot de passe en clair et empreinte str ou bytes.
    Fait : checkpw. Une empreinte illisible vaut False.
    Retour : True si le mot de passe correspond.
    """
    try:
        attendue = empreinte.encode("utf-8") if isinstance(empreinte, str) else empreinte
        return bcrypt.checkpw(mot_de_passe.encode("utf-8"), attendue)
    except ValueError:
        return False


def authentifier(session: Session, username: str, password: str) -> Utilisateur | None:
    """Vérifie l'identifiant et le mot de passe.

    Entrée : session, username, password.
    Fait : un compte inconnu est comparé à l'empreinte fictive. Le message d'échec est décidé par la route.
    Retour : l'utilisateur, ou None si le compte manque ou si le mot de passe est faux.
    """
    utilisateur = session.scalar(select(Utilisateur).where(Utilisateur.username == username))
    empreinte = utilisateur.mot_de_passe_hash if utilisateur is not None else _empreinte_fictive()
    if not mot_de_passe_valide(password, empreinte) or utilisateur is None:
        return None
    return utilisateur


def emettre_jeton(username: str, role: str) -> str:
    """Signe un JWT HS256.

    Entrée : identifiant et rôle.
    Fait : charge sub, role, exp. Durée JWT_EXPIRATION_MINUTES, secret JWT_SECRET.
    Retour : le jeton en str.
    """
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
    """Dépendance : jeton Bearer obligatoire.

    Entrée : en-tête Authorization, ou rien.
    Fait : refuse un jeton absent, un mauvais schéma, une signature fausse, une exp manquante ou un rôle hors exploitant et direction.
    Retour : {username, role}. Sinon 401 « Jeton absent, invalide ou expire ».
    """
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
    """Dépendance : le rôle doit être exploitant.

    Entrée : l'utilisateur déjà authentifié.
    Fait : un autre rôle lève 403 « Acces reserve au role exploitant ».
    Retour : le même dictionnaire {username, role}.
    """
    if utilisateur["role"] != "exploitant":
        raise HTTPException(status_code=403, detail="Acces reserve au role exploitant")
    return utilisateur


def _secret() -> str:
    """Lit JWT_SECRET. Vide ou absent : RuntimeError, pas de secret en dur.

    Entrée : la variable d'environnement JWT_SECRET.
    Fait : refuse une valeur vide.
    Retour : le secret utilisé pour signer et vérifier le JWT.
    """
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET est absent de l'environnement")
    return secret


def _duree_minutes() -> int:
    """Lit JWT_EXPIRATION_MINUTES. Défaut 60.

    Entrée : la variable d'environnement, ou 60 si elle est absente.
    Fait : exige un entier strictement positif. Sinon RuntimeError.
    Retour : la durée de validité du jeton, en minutes.
    """
    brut = os.environ.get("JWT_EXPIRATION_MINUTES", "60").strip()
    try:
        duree = int(brut)
    except ValueError as erreur:
        raise RuntimeError("JWT_EXPIRATION_MINUTES n'est pas un entier") from erreur
    if duree <= 0:
        raise RuntimeError("JWT_EXPIRATION_MINUTES doit être strictement positif")
    return duree
