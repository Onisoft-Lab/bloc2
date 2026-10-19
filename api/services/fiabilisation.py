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
    """Issue d'une règle de fiabilisation, sans accès à la base.

    Entrée : construite par la règle, à partir d'une valeur brute du CSV.
    Fait : porte la valeur retenue, ou le motif si la valeur est écartée.
    Retour : acceptee, valeur, motif, colonne, normalisee, avertissement.
    """

    acceptee: bool
    valeur: object = None
    motif: str | None = None
    colonne: str | None = None
    normalisee: bool = False
    avertissement: bool = False


class CibleNormalisee(NamedTuple):
    """Cible d'incident après RG6 : un vélo ou une station, jamais les deux.

    Entrée : produite par valider_coherence_cible.
    Fait : fige cible, velo_id et station_id cohérents.
    Retour : les trois champs. La référence qui ne s'applique pas vaut None.
    """

    cible: str
    velo_id: str | None
    station_id: str | None


def est_doublon(empreinte: str, empreintes_vues: set[str]) -> bool:
    """Une ligne déjà rencontrée dans le même fichier ne s'importe qu'une fois.

    Entrée : empreinte de la ligne brute et l'ensemble déjà vu dans ce fichier.
    Fait : teste la présence, sans modifier l'ensemble.
    Retour : True si la ligne est un doublon strict.
    """
    return empreinte in empreintes_vues


def normaliser_velo_id(valeur: str) -> Resultat:
    """Identifiant vélo : V suivi de 4 chiffres.

    Entrée : chaîne CSV, espaces ignorés.
    Fait : passe en majuscules. Une casse différente est une normalisation.
    Retour : Resultat accepté ou rejeté, colonne velo_id.
    """
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
    """RG1. Identifiant station : S suivi de 3 chiffres.

    Entrée : chaîne CSV, espaces ignorés.
    Fait : passe en majuscules. Une casse différente est une normalisation.
    Retour : Resultat accepté ou rejeté, colonne station_id.
    """
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
    """RG1. Capacité entière strictement positive.

    Entrée : chaîne CSV.
    Fait : convertit en entier. Refuse 0, un négatif et un texte.
    Retour : Resultat accepté (int) ou rejeté, colonne capacite.
    """
    try:
        capacite = int((valeur or "").strip())
    except ValueError:
        return Resultat(False, motif="Capacité invalide", colonne="capacite")
    if capacite <= 0:
        return Resultat(False, motif="Capacité non strictement positive", colonne="capacite")
    return Resultat(True, valeur=capacite, colonne="capacite")


def valider_coordonnee(valeur: str, colonne: str) -> Resultat:
    """Latitude ou longitude numérique.

    Entrée : chaîne CSV et le nom de colonne, latitude ou longitude.
    Fait : convertit en Decimal. Un texte est rejeté.
    Retour : Resultat accepté (Decimal) ou rejeté, colonne demandée.
    """
    try:
        nombre = Decimal((valeur or "").strip())
    except InvalidOperation:
        return Resultat(False, motif="Coordonnée invalide", colonne=colonne)
    return Resultat(True, valeur=nombre, colonne=colonne)


def valider_texte_obligatoire(valeur: str, colonne: str) -> Resultat:
    """Champ texte obligatoire, après retrait des espaces.

    Entrée : chaîne CSV et le nom de colonne.
    Fait : rejette une valeur vide.
    Retour : Resultat accepté (texte) ou rejeté, colonne demandée.
    """
    brut = (valeur or "").strip()
    if not brut:
        return Resultat(False, motif="Valeur obligatoire absente", colonne=colonne)
    return Resultat(True, valeur=brut, colonne=colonne)


def normaliser_date(valeur: str) -> Resultat:
    """Date de mise en service d'une station.

    Entrée : chaîne CSV.
    Fait : accepte AAAA-MM-JJ. JJ/MM/AAAA est normalisé.
    Retour : Resultat accepté (date) ou rejeté, colonne date_mise_en_service.
    """
    return _parser_date(valeur, (("%Y-%m-%d", False), ("%d/%m/%Y", True)), "date_mise_en_service")


def normaliser_horodatage_trajet(valeur: str) -> Resultat:
    """Horodatage de départ d'un trajet, obligatoire.

    Entrée : chaîne CSV.
    Fait : accepte AAAA-MM-JJ HH:MM:SS. Les formats jour/mois ou sans secondes sont normalisés.
    Retour : Resultat accepté (datetime) ou rejeté, colonne depart_horodatage.
    """
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
    """Horodatage de signalement, obligatoire.

    Entrée : chaîne CSV.
    Fait : accepte AAAA-MM-JJ HH:MM. Les autres formats reconnus sont normalisés.
    Retour : Resultat accepté (datetime) ou rejeté, colonne date_signalement.
    """
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
    """Horodatage facultatif.

    Entrée : chaîne CSV et le nom de colonne.
    Fait : vide accepté. Un format incorrect est rejeté. JJ/MM/AAAA est normalisé.
    Retour : Resultat accepté (datetime ou None) ou rejeté.
    """
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
    """RG4. Durée entière strictement positive, en secondes.

    Entrée : chaîne CSV.
    Fait : refuse 0, un négatif et un texte.
    Retour : Resultat accepté (int) ou rejeté, colonne duree_secondes.
    """
    try:
        duree = int((valeur or "").strip())
    except ValueError:
        return Resultat(False, motif="Durée invalide", colonne="duree_secondes")
    if duree <= 0:
        return Resultat(False, motif="Durée nulle ou négative", colonne="duree_secondes")
    return Resultat(True, valeur=duree, colonne="duree_secondes")


def valider_station_depart(station_id: str, stations: set[str]) -> Resultat:
    """RG2. La station de départ existe dans le référentiel retenu.

    Entrée : identifiant brut et l'ensemble des stations déjà importables.
    Fait : vide ou absent du référentiel, rejeté.
    Retour : Resultat accepté ou rejeté, colonne station_depart.
    """
    identifiant = (station_id or "").strip()
    if not identifiant or identifiant not in stations:
        return Resultat(False, motif="Station de départ inconnue", colonne="station_depart")
    return Resultat(True, valeur=identifiant, colonne="station_depart")


def valider_station_arrivee(station_id: str, stations: set[str]) -> Resultat:
    """RG3. Arrivée facultative, sinon station du référentiel.

    Entrée : identifiant brut et l'ensemble des stations déjà retenues.
    Fait : vide accepté (valeur None) ; inconnu, dont S999, rejeté.
    Retour : Resultat accepté ou rejeté, colonne station_arrivee.
    """
    identifiant = (station_id or "").strip()
    if not identifiant:
        return Resultat(True, valeur=None, colonne="station_arrivee")
    if identifiant not in stations:
        return Resultat(False, motif="Station d'arrivée inconnue", colonne="station_arrivee")
    return Resultat(True, valeur=identifiant, colonne="station_arrivee")


def normaliser_type_usager(valeur: str) -> Resultat:
    """Type d'usager : abonne ou occasionnel.

    Entrée : chaîne CSV.
    Fait : passe en minuscules. Une casse différente est une normalisation.
    Retour : Resultat accepté ou rejeté, colonne type_usager.
    """
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
    """RG5. Pseudonyme selon le type d'usager.

    Entrée : type déjà normalisé et usager_ref brut.
    Fait : occasionnel avec pseudonyme rejeté. Abonné sans pseudonyme accepté avec avertissement. Format attendu : U et 8 hexadécimaux.
    Retour : Resultat accepté (référence ou None) ou rejeté, colonne usager_ref.
    """
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
    """RG7. Statut ouvert, en_cours ou resolu.

    Entrée : chaîne CSV.
    Fait : minuscules, espaces remplacés par des soulignés. « En cours » devient en_cours.
    Retour : Resultat accepté ou rejeté, colonne statut.
    """
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
    """RG6. Un incident vise un vélo ou une station, jamais les deux.

    Entrée : cible, velo_id et station_id bruts, et les stations retenues.
    Fait : vélo exige un vélo valide et aucune station. Station exige une station du référentiel et aucun vélo.
    Retour : Resultat dont la valeur est une CibleNormalisee, ou un rejet.
    """
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
    """RG8. La date de résolution suit le statut.

    Entrée : statut normalisé, signalement, résolution éventuelle.
    Fait : résolu exige une résolution postérieure ou égale au signalement. Un autre statut refuse une résolution renseignée.
    Retour : Resultat accepté (datetime ou None) ou rejeté, colonne date_resolution.
    """
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
    """RG8. Technicien attendu dès la prise en charge, sans rejet.

    Entrée : statut normalisé et nom brut.
    Fait : en_cours ou resolu sans nom reste accepté, avec avertissement.
    Retour : Resultat toujours accepté. La valeur vaut None si le nom est vide.
    """
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
    """Parse un horodatage obligatoire selon une liste de formats.

    Entrée : chaîne, formats (motif strptime, True si ce motif est une normalisation), colonne.
    Fait : essaie les formats dans l'ordre. Vide ou aucun format reconnu : rejet.
    Retour : Resultat accepté (datetime) ou rejeté.
    """
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
    """Parse une date obligatoire selon une liste de formats.

    Entrée : chaîne, formats (motif strptime, True si ce motif est une normalisation), colonne.
    Fait : essaie les formats dans l'ordre. Vide ou aucun format reconnu : rejet.
    Retour : Resultat accepté (date) ou rejeté.
    """
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
