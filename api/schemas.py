"""Schémas Pydantic exposés par l'API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Lecture(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DemandeConnexion(BaseModel):
    username: str
    password: str


class Jeton(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: str


class StationLecture(Lecture):
    station_id: str
    nom: str
    commune: str
    capacite: int
    latitude: float
    longitude: float
    date_mise_en_service: date


class TrajetLecture(Lecture):
    trajet_id: str
    velo_id: str
    depart_horodatage: datetime
    station_depart: str
    station_arrivee: str | None
    duree_secondes: int
    type_usager: str
    usager_ref: str | None


class IncidentLecture(Lecture):
    incident_id: str
    date_signalement: datetime
    cible: str
    velo_id: str | None
    station_id: str | None
    type_incident: str
    statut: str
    date_resolution: datetime | None
    technicien: str | None


class PageStations(BaseModel):
    total: int
    page: int
    taille_page: int
    resultats: list[StationLecture]


class PageTrajets(BaseModel):
    total: int
    page: int
    taille_page: int
    resultats: list[TrajetLecture]


class PageIncidents(BaseModel):
    total: int
    page: int
    taille_page: int
    resultats: list[IncidentLecture]


class MajStatut(BaseModel):
    """Corps du PUT statut : en_cours ou resolu, jamais ouvert."""

    statut: Literal["en_cours", "resolu"]


class ActiviteJour(BaseModel):
    jour: date
    nb_trajets: int


class ReponseActivite(BaseModel):
    donnees: list[ActiviteJour]


class StationActive(BaseModel):
    station_id: str
    nom: str
    nb_departs: int
    nb_arrivees: int


class ReponseStationsActives(BaseModel):
    donnees: list[StationActive]


class IncidentStatut(BaseModel):
    statut: str
    nb_incidents: int


class ReponseIncidentsStatut(BaseModel):
    donnees: list[IncidentStatut]
    delai_moyen_resolution_heures: float | None
