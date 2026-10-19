"""Connexion PostgreSQL (SQLAlchemy 2) lue depuis l'environnement."""

import os
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

RACINE = Path(__file__).resolve().parents[1]
load_dotenv(RACINE / ".env")


def _url_base() -> str:
    """Lit DATABASE_URL. Absente : arrêt immédiat, pas d'URL en dur.

    Entrée : la variable d'environnement DATABASE_URL.
    Fait : refuse une valeur vide.
    Retour : l'URL SQLAlchemy de la base veloville.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL est absente de l'environnement")
    return url


engine = create_engine(_url_base(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Ouvre une session SQLAlchemy pour la requête et la ferme ensuite.

    Entrée : aucune. L'URL vient de l'environnement au démarrage.
    Fait : yield la session, close dans le finally.
    Retour : générateur de Session, dépendance FastAPI.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
