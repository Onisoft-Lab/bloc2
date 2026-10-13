"""Fixtures pytest. Les secrets sont lus dans l'environnement, jamais en dur."""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

RACINE = Path(__file__).resolve().parents[1]
load_dotenv(RACINE / ".env")


def mot_de_passe() -> str:
    valeur = os.environ.get("COMPTE_MOT_DE_PASSE", "").strip().strip("'\"")
    if not valeur:
        raise RuntimeError("COMPTE_MOT_DE_PASSE est absent de l'environnement")
    return valeur


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def jeton_exploitant(client: TestClient) -> str:
    return _jeton(client, "exploitant01")


@pytest.fixture(scope="session")
def jeton_direction(client: TestClient) -> str:
    return _jeton(client, "direction01")


@pytest.fixture
def session() -> Generator[Session, None, None]:
    from api.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def _jeton(client: TestClient, username: str) -> str:
    reponse = client.post(
        "/auth/login",
        json={"username": username, "password": mot_de_passe()},
    )
    assert reponse.status_code == 200, reponse.text
    return reponse.json()["access_token"]
