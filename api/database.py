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
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL est absente de l'environnement")
    return url


engine = create_engine(_url_base(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
