"""Règles de fiabilisation, pures : aucun accès à la base.

Chaque fonction accepte une valeur brute et retourne un résultat accepté,
éventuellement normalisé, ou un motif de rejet.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

STATUTS = frozenset({"ouvert", "en_cours", "resolu"})
TYPES_USAGER = frozenset({"abonne", "occasionnel"})
_VELO = re.compile(r"^V\d{4}$")
_STATION = re.compile(r"^S\d{3}$")
_USAGER = re.compile(r"^U[0-9a-fA-F]{8}$")


@dataclass(frozen=True)
class Resultat:
    acceptee: bool
    valeur: object = None
    motif: str | None = None
    colonne: str | None = None
    normalisee: bool = False
    avertissement: bool = False


class CibleNormalisee(NamedTuple):
    cible: str
    velo_id: str | None
    station_id: str | None


def est_doublon(empreinte: str, empreintes_vues: set[str]) -> bool:
    """Une ligne déjà rencontrée dans le même fichier ne s'importe qu'une fois."""
    return empreinte in empreintes_vues


def normaliser_velo_id(valeur: str) -> Resultat:
    brut = (valeur or "").strip()
    candidat = brut.upper()
    if not _VELO.fullmatch(candidat):
        return Resultat(False, motif="Identifiant de vélo invalide", colonne="velo_id")
    if candidat == brut:
        return Resultat(True, valeur=candidat, colonne="velo_id")
    return Resultat(
        True,
        valeur=candidat,
        colonne="velo_id",
        normalisee=True,
        motif="Casse de l'identifiant vélo normalisée",
    )


def valider_identifiant_station(valeur: str) -> Resultat:
    brut = (valeur or "").strip()
    candidat = brut.upper()
    if not _STATION.fullmatch(candidat):
        return Resultat(False, motif="Identifiant de station invalide", colonne="station_id")
    if candidat == brut:
        return Resultat(True, valeur=candidat, colonne="station_id")
    return Resultat(
        True,
        valeur=candidat,
        colonne="station_id",
        normalisee=True,
        motif="Casse de l'identifiant de station normalisée",
    )


def valider_capacite(valeur: str) -> Resultat:
    try:
        capacite = int((valeur or "").strip())
    except ValueError:
        return Resultat(False, motif="Capacité invalide", colonne="capacite")
    if capacite <= 0:
        return Resultat(False, motif="Capacité non strictement positive", colonne="capacite")
    return Resultat(True, valeur=capacite, colonne="capacite")


def valider_coordonnee(valeur: str, colonne: str) -> Resultat:
    try:
        nombre = Decimal((valeur or "").strip())
    except InvalidOperation:
        return Resultat(False, motif="Coordonnée invalide", colonne=colonne)
    return Resultat(True, valeur=nombre, colonne=colonne)


def valider_texte_obligatoire(valeur: str, colonne: str) -> Resultat:
    brut = (valeur or "").strip()
    if not brut:
        return Resultat(False, motif="Valeur obligatoire absente", colonne=colonne)
    return Resultat(True, valeur=brut, colonne=colonne)


def normaliser_date(valeur: str) -> Resultat:
    return _parser_date(valeur, (("%Y-%m-%d", False), ("%d/%m/%Y", True)), "date_mise_en_service")


def normaliser_horodatage_trajet(valeur: str) -> Resultat:
    return _parser_horodatage(
        valeur,
        (
            ("%Y-%m-%d %H:%M:%S", False),
            ("%d/%m/%Y %H:%M:%S", True),
            ("%d/%m/%Y %H:%M", True),
            ("%Y-%m-%d %H:%M", True),
        ),
        "depart_horodatage",
    )


def normaliser_horodatage_incident(valeur: str) -> Resultat:
    return _parser_horodatage(
        valeur,
        (
            ("%Y-%m-%d %H:%M", False),
            ("%Y-%m-%d %H:%M:%S", True),
            ("%d/%m/%Y %H:%M", True),
            ("%d/%m/%Y %H:%M:%S", True),
        ),
        "date_signalement",
    )


def parser_horodatage_optionnel(valeur: str, colonne: str) -> Resultat:
    """Horodatage facultatif : vide accepté, format incorrect rejeté."""
    if not (valeur or "").strip():
        return Resultat(True, valeur=None, colonne=colonne)
    resultat = _parser_horodatage(
        valeur,
        (
            ("%Y-%m-%d %H:%M", False),
            ("%Y-%m-%d %H:%M:%S", True),
            ("%d/%m/%Y %H:%M", True),
            ("%d/%m/%Y %H:%M:%S", True),
        ),
        colonne,
    )
    return resultat


def valider_duree_secondes(valeur: str) -> Resultat:
    try:
        duree = int((valeur or "").strip())
    except ValueError:
        return Resultat(False, motif="Durée invalide", colonne="duree_secondes")
    if duree <= 0:
        return Resultat(False, motif="Durée nulle ou négative", colonne="duree_secondes")
    return Resultat(True, valeur=duree, colonne="duree_secondes")


def valider_station_depart(station_id: str, stations: set[str]) -> Resultat:
    identifiant = (station_id or "").strip()
    if not identifiant or identifiant not in stations:
        return Resultat(False, motif="Station de départ inconnue", colonne="station_depart")
    return Resultat(True, valeur=identifiant, colonne="station_depart")


def valider_station_arrivee(station_id: str, stations: set[str]) -> Resultat:
    identifiant = (station_id or "").strip()
    if not identifiant:
        return Resultat(True, valeur=None, colonne="station_arrivee")
    if identifiant not in stations:
        return Resultat(False, motif="Station d'arrivée inconnue", colonne="station_arrivee")
    return Resultat(True, valeur=identifiant, colonne="station_arrivee")


def normaliser_type_usager(valeur: str) -> Resultat:
    brut = (valeur or "").strip()
    cle = brut.lower()
    if cle not in TYPES_USAGER:
        return Resultat(False, motif="Type d'usager inconnu", colonne="type_usager")
    if cle == brut:
        return Resultat(True, valeur=cle, colonne="type_usager")
    return Resultat(
        True,
        valeur=cle,
        colonne="type_usager",
        normalisee=True,
        motif="Casse du type d'usager normalisée",
    )


def valider_usager_ref(type_usager: str, usager_ref: str) -> Resultat:
    reference = (usager_ref or "").strip()
    if type_usager == "occasionnel":
        if reference:
            return Resultat(
                False,
                motif="Un usager occasionnel ne doit pas avoir de pseudonyme",
                colonne="usager_ref",
            )
        return Resultat(True, valeur=None, colonne="usager_ref")
    if not reference:
        return Resultat(
            True,
            valeur=None,
            colonne="usager_ref",
            avertissement=True,
            motif="Pseudonyme d'abonné absent",
        )
    if not _USAGER.fullmatch(reference):
        return Resultat(False, motif="Pseudonyme d'usager invalide", colonne="usager_ref")
    return Resultat(True, valeur=reference, colonne="usager_ref")


def normaliser_statut(valeur: str) -> Resultat:
    brut = (valeur or "").strip()
    cle = brut.lower().replace(" ", "_")
    if cle not in STATUTS:
        return Resultat(False, motif="Statut hors des valeurs autorisées", colonne="statut")
    if cle == brut:
        return Resultat(True, valeur=cle, colonne="statut")
    return Resultat(
        True,
        valeur=cle,
        colonne="statut",
        normalisee=True,
        motif="Casse ou libellé de statut normalisé",
    )


def valider_coherence_cible(
    cible: str,
    velo_id: str,
    station_id: str,
    stations: set[str],
) -> Resultat:
    brut = (cible or "").strip()
    nature = brut.lower()
    velo = (velo_id or "").strip()
    station = (station_id or "").strip()
    if nature not in {"velo", "station"}:
        return Resultat(False, motif="Cible inconnue", colonne="cible")

    if nature == "velo":
        if not velo or station:
            return Resultat(
                False,
                motif="Un incident vélo doit référencer un vélo et aucune station",
                colonne="cible",
            )
        velo_normalise = normaliser_velo_id(velo)
        if not velo_normalise.acceptee:
            return velo_normalise
        return Resultat(
            True,
            valeur=CibleNormalisee(nature, str(velo_normalise.valeur), None),
            colonne="cible",
            normalisee=bool(velo_normalise.normalisee or brut != nature),
            motif="Cible ou identifiant de vélo normalisé" if velo_normalise.normalisee or brut != nature else None,
        )

    if not station or velo:
        return Resultat(
            False,
            motif="Un incident station doit référencer une station et aucun vélo",
            colonne="cible",
        )
    if station not in stations:
        return Resultat(False, motif="Station visée inconnue", colonne="station_id")
    return Resultat(
        True,
        valeur=CibleNormalisee(nature, None, station),
        colonne="cible",
        normalisee=brut != nature,
        motif="Casse de la cible normalisée" if brut != nature else None,
    )


def valider_coherence_dates(
    statut: str,
    signalement: datetime,
    resolution: datetime | None,
) -> Resultat:
    if statut == "resolu":
        if resolution is None:
            return Resultat(
                False,
                motif="Date de résolution absente pour un incident résolu",
                colonne="date_resolution",
            )
        if resolution < signalement:
            return Resultat(
                False,
                motif="Date de résolution antérieure au signalement",
                colonne="date_resolution",
            )
        return Resultat(True, valeur=resolution, colonne="date_resolution")
    if resolution is not None:
        return Resultat(
            False,
            motif="Date de résolution renseignée alors que l'incident n'est pas résolu",
            colonne="date_resolution",
        )
    return Resultat(True, valeur=None, colonne="date_resolution")


def avertir_technicien_absent(statut: str, technicien: str) -> Resultat:
    nom = (technicien or "").strip()
    if statut in {"en_cours", "resolu"} and not nom:
        return Resultat(
            True,
            valeur=None,
            colonne="technicien",
            avertissement=True,
            motif="Technicien absent pour un incident pris en charge",
        )
    return Resultat(True, valeur=nom or None, colonne="technicien")


def _parser_horodatage(valeur: str, formats: tuple[tuple[str, bool], ...], colonne: str) -> Resultat:
    brut = (valeur or "").strip()
    if not brut:
        return Resultat(False, motif="Horodatage absent", colonne=colonne)
    for fmt, a_normaliser in formats:
        try:
            moment = datetime.strptime(brut, fmt)
        except ValueError:
            continue
        if a_normaliser:
            return Resultat(
                True,
                valeur=moment,
                colonne=colonne,
                normalisee=True,
                motif="Format d'horodatage normalisé",
            )
        return Resultat(True, valeur=moment, colonne=colonne)
    return Resultat(False, motif="Format d'horodatage invalide", colonne=colonne)


def _parser_date(valeur: str, formats: tuple[tuple[str, bool], ...], colonne: str) -> Resultat:
    brut = (valeur or "").strip()
    if not brut:
        return Resultat(False, motif="Date absente", colonne=colonne)
    for fmt, a_normaliser in formats:
        try:
            jour: date = datetime.strptime(brut, fmt).date()
        except ValueError:
            continue
        if a_normaliser:
            return Resultat(
                True,
                valeur=jour,
                colonne=colonne,
                normalisee=True,
                motif="Format de date normalisé",
            )
        return Resultat(True, valeur=jour, colonne=colonne)
    return Resultat(False, motif="Format de date invalide", colonne=colonne)
