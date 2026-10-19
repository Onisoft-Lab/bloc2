"""Modèles SQLAlchemy des tables du contrat VéloVille."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Station(Base):
    """Table station, clé station_id."""

    __tablename__ = "station"

    station_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    nom: Mapped[str] = mapped_column(Text, nullable=False)
    commune: Mapped[str] = mapped_column(Text, nullable=False)
    capacite: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(8, 5), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(8, 5), nullable=False)
    date_mise_en_service: Mapped[date] = mapped_column(Date, nullable=False)


class Trajet(Base):
    """Table trajet, clé trajet_id. usager_ref est renvoyé par l'API."""

    __tablename__ = "trajet"

    trajet_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    velo_id: Mapped[str] = mapped_column(String(8), nullable=False)
    depart_horodatage: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    station_depart: Mapped[str] = mapped_column(ForeignKey("station.station_id"), nullable=False)
    station_arrivee: Mapped[str | None] = mapped_column(ForeignKey("station.station_id"))
    duree_secondes: Mapped[int] = mapped_column(Integer, nullable=False)
    type_usager: Mapped[str] = mapped_column(String(20), nullable=False)
    usager_ref: Mapped[str | None] = mapped_column(String(20))


class Incident(Base):
    """Table incident, clé incident_id."""

    __tablename__ = "incident"

    incident_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    date_signalement: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cible: Mapped[str] = mapped_column(String(10), nullable=False)
    velo_id: Mapped[str | None] = mapped_column(String(8))
    station_id: Mapped[str | None] = mapped_column(ForeignKey("station.station_id"))
    type_incident: Mapped[str] = mapped_column(Text, nullable=False)
    statut: Mapped[str] = mapped_column(String(10), nullable=False)
    date_resolution: Mapped[datetime | None] = mapped_column(DateTime)
    technicien: Mapped[str | None] = mapped_column(Text)


class Utilisateur(Base):
    """Table utilisateur, clé id_utilisateur. Mot de passe stocké en bcrypt."""

    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    mot_de_passe_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
