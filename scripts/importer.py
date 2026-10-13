"""Import et fiabilisation des trois exports CSV dans PostgreSQL.

Usage : python scripts/importer.py [--dossier data]

Le script est idempotent : une seconde exécution ne crée ni doublon ni erreur.
Le journal est réécrit à chaque exécution dans docs/journal-import.csv.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as inserer_pg

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from api.database import SessionLocal  # noqa: E402
from api.models import Incident, Station, Trajet  # noqa: E402
from api.services.fiabilisation import (  # noqa: E402
    Resultat,
    avertir_technicien_absent,
    est_doublon,
    normaliser_date,
    normaliser_horodatage_incident,
    normaliser_horodatage_trajet,
    normaliser_statut,
    normaliser_type_usager,
    normaliser_velo_id,
    parser_horodatage_optionnel,
    valider_capacite,
    valider_coherence_cible,
    valider_coherence_dates,
    valider_coordonnee,
    valider_duree_secondes,
    valider_identifiant_station,
    valider_station_arrivee,
    valider_station_depart,
    valider_texte_obligatoire,
    valider_usager_ref,
)

COLONNES_JOURNAL = ["fichier", "identifiant", "colonne", "valeur", "motif", "decision"]
JOURNAL = RACINE / "docs" / "journal-import.csv"

COLONNES_STATION = [
    "station_id",
    "nom",
    "commune",
    "capacite",
    "latitude",
    "longitude",
    "date_mise_en_service",
]
COLONNES_TRAJET = [
    "trajet_id",
    "velo_id",
    "depart_horodatage",
    "station_depart",
    "station_arrivee",
    "duree_secondes",
    "type_usager",
    "usager_ref",
]
COLONNES_INCIDENT = [
    "incident_id",
    "date_signalement",
    "cible",
    "velo_id",
    "station_id",
    "type_incident",
    "statut",
    "date_resolution",
    "technicien",
]


@dataclass
class Bilan:
    fichier: str
    lues: int = 0
    retenues: int = 0
    rejetees: int = 0
    doublons: int = 0


def main() -> None:
    arguments = argparse.ArgumentParser(description="Importe et fiabilise les exports VéloVille")
    arguments.add_argument("--dossier", default="data", help="Dossier contenant les trois CSV")
    args = arguments.parse_args()
    dossier = Path(args.dossier)
    if not dossier.is_dir():
        dossier = RACINE / args.dossier
    if not dossier.is_dir():
        raise SystemExit(f"Dossier d'exports introuvable : {args.dossier}")

    stations_brutes = lire_csv(dossier / "stations.csv", COLONNES_STATION)
    trajets_bruts = lire_csv(dossier / "trajets.csv", COLONNES_TRAJET)
    incidents_bruts = lire_csv(dossier / "incidents.csv", COLONNES_INCIDENT)

    stations, journal_stations, bilan_stations = traiter_stations(stations_brutes)
    stations_connues = {ligne["station_id"] for ligne in stations}
    trajets, journal_trajets, bilan_trajets = traiter_trajets(trajets_bruts, stations_connues)
    incidents, journal_incidents, bilan_incidents = traiter_incidents(incidents_bruts, stations_connues)

    for bilan in (bilan_stations, bilan_trajets, bilan_incidents):
        if bilan.retenues + bilan.rejetees + bilan.doublons != bilan.lues:
            raise SystemExit(f"Comptage incohérent pour {bilan.fichier}")

    with SessionLocal() as session:
        inserer(session, Station, stations, "station_id")
        inserer(session, Trajet, trajets, "trajet_id")
        inserer(session, Incident, incidents, "incident_id")
        session.commit()
        comptes = {
            nom: int(session.scalar(text(f"SELECT count(*) FROM {nom}")) or 0)
            for nom in ("station", "trajet", "incident")
        }

    ecrire_journal(journal_stations + journal_trajets + journal_incidents, JOURNAL)
    for bilan in (bilan_stations, bilan_trajets, bilan_incidents):
        print(
            f"{bilan.fichier} : {bilan.lues} lues, {bilan.retenues} retenues, "
            f"{bilan.rejetees} rejetées, {bilan.doublons} doublons"
        )
    print(
        "Base : "
        f"station={comptes['station']} trajet={comptes['trajet']} incident={comptes['incident']}"
    )
    print(f"Journal : {JOURNAL.relative_to(RACINE)}")


def lire_csv(chemin: Path, colonnes: list[str]) -> list[dict[str, str]]:
    if not chemin.is_file():
        raise SystemExit(f"Export introuvable : {chemin}")
    table = pd.read_csv(chemin, dtype=str, keep_default_na=False, encoding="utf-8")
    manquantes = [colonne for colonne in colonnes if colonne not in table.columns]
    if manquantes:
        raise SystemExit(f"Colonnes absentes dans {chemin.name} : {', '.join(manquantes)}")
    return table.to_dict(orient="records")


def traiter_stations(lignes: list[dict[str, str]]) -> tuple[list[dict], list[dict], Bilan]:
    bilan = Bilan("stations.csv", lues=len(lignes))
    journal: list[dict] = []
    retenues: list[dict] = []
    empreintes: set[str] = set()
    identifiants: set[str] = set()
    for ligne in lignes:
        identifiant = (ligne["station_id"] or "").strip()
        if _ecarter_doublon(ligne, COLONNES_STATION, empreintes, identifiants, identifiant, "stations.csv", journal, bilan):
            continue
        notes: list[dict] = []
        controles = [
            (valider_identifiant_station(ligne["station_id"]), ligne["station_id"]),
            (valider_texte_obligatoire(ligne["nom"], "nom"), ligne["nom"]),
            (valider_texte_obligatoire(ligne["commune"], "commune"), ligne["commune"]),
            (valider_capacite(ligne["capacite"]), ligne["capacite"]),
            (valider_coordonnee(ligne["latitude"], "latitude"), ligne["latitude"]),
            (valider_coordonnee(ligne["longitude"], "longitude"), ligne["longitude"]),
            (normaliser_date(ligne["date_mise_en_service"]), ligne["date_mise_en_service"]),
        ]
        if not _controler(controles, notes, journal, bilan, "stations.csv", identifiant):
            continue
        identifiant_normalise, nom, commune, capacite, latitude, longitude, mise_en_service = (
            controle.valeur for controle, _brute in controles
        )
        retenues.append(
            {
                "station_id": identifiant_normalise,
                "nom": nom,
                "commune": commune,
                "capacite": capacite,
                "latitude": latitude,
                "longitude": longitude,
                "date_mise_en_service": mise_en_service,
            }
        )
        bilan.retenues += 1
        journal.extend(notes)
    return retenues, journal, bilan


def traiter_trajets(
    lignes: list[dict[str, str]],
    stations: set[str],
) -> tuple[list[dict], list[dict], Bilan]:
    bilan = Bilan("trajets.csv", lues=len(lignes))
    journal: list[dict] = []
    retenues: list[dict] = []
    empreintes: set[str] = set()
    identifiants: set[str] = set()
    for ligne in lignes:
        identifiant = (ligne["trajet_id"] or "").strip()
        if _ecarter_doublon(ligne, COLONNES_TRAJET, empreintes, identifiants, identifiant, "trajets.csv", journal, bilan):
            continue
        notes: list[dict] = []
        velo = normaliser_velo_id(ligne["velo_id"])
        horodatage = normaliser_horodatage_trajet(ligne["depart_horodatage"])
        duree = valider_duree_secondes(ligne["duree_secondes"])
        depart = valider_station_depart(ligne["station_depart"], stations)
        arrivee = valider_station_arrivee(ligne["station_arrivee"], stations)
        type_usager = normaliser_type_usager(ligne["type_usager"])
        controles = [
            (velo, ligne["velo_id"]),
            (horodatage, ligne["depart_horodatage"]),
            (duree, ligne["duree_secondes"]),
            (depart, ligne["station_depart"]),
            (arrivee, ligne["station_arrivee"]),
            (type_usager, ligne["type_usager"]),
        ]
        if not _controler(controles, notes, journal, bilan, "trajets.csv", identifiant):
            continue
        reference = valider_usager_ref(str(type_usager.valeur), ligne["usager_ref"])
        if not _controler([(reference, ligne["usager_ref"])], notes, journal, bilan, "trajets.csv", identifiant):
            continue
        retenues.append(
            {
                "trajet_id": identifiant,
                "velo_id": velo.valeur,
                "depart_horodatage": horodatage.valeur,
                "station_depart": depart.valeur,
                "station_arrivee": arrivee.valeur,
                "duree_secondes": duree.valeur,
                "type_usager": type_usager.valeur,
                "usager_ref": reference.valeur,
            }
        )
        bilan.retenues += 1
        journal.extend(notes)
    return retenues, journal, bilan


def traiter_incidents(
    lignes: list[dict[str, str]],
    stations: set[str],
) -> tuple[list[dict], list[dict], Bilan]:
    bilan = Bilan("incidents.csv", lues=len(lignes))
    journal: list[dict] = []
    retenues: list[dict] = []
    empreintes: set[str] = set()
    identifiants: set[str] = set()
    for ligne in lignes:
        identifiant = (ligne["incident_id"] or "").strip()
        if _ecarter_doublon(
            ligne, COLONNES_INCIDENT, empreintes, identifiants, identifiant, "incidents.csv", journal, bilan
        ):
            continue
        notes: list[dict] = []
        signalement = normaliser_horodatage_incident(ligne["date_signalement"])
        statut = normaliser_statut(ligne["statut"])
        resolution = parser_horodatage_optionnel(ligne["date_resolution"], "date_resolution")
        type_incident = valider_texte_obligatoire(ligne["type_incident"], "type_incident")
        controles = [
            (signalement, ligne["date_signalement"]),
            (statut, ligne["statut"]),
            (resolution, ligne["date_resolution"]),
            (type_incident, ligne["type_incident"]),
        ]
        if not _controler(controles, notes, journal, bilan, "incidents.csv", identifiant):
            continue
        cible = valider_coherence_cible(ligne["cible"], ligne["velo_id"], ligne["station_id"], stations)
        if not _controler([(cible, ligne["cible"])], notes, journal, bilan, "incidents.csv", identifiant):
            continue
        dates = valider_coherence_dates(str(statut.valeur), signalement.valeur, resolution.valeur)
        if not _controler([(dates, ligne["date_resolution"])], notes, journal, bilan, "incidents.csv", identifiant):
            continue
        technicien = avertir_technicien_absent(str(statut.valeur), ligne["technicien"])
        _noter(technicien, ligne["technicien"], notes, "incidents.csv", identifiant)
        cible_normalisee = cible.valeur
        retenues.append(
            {
                "incident_id": identifiant,
                "date_signalement": signalement.valeur,
                "cible": cible_normalisee.cible,
                "velo_id": cible_normalisee.velo_id,
                "station_id": cible_normalisee.station_id,
                "type_incident": type_incident.valeur,
                "statut": statut.valeur,
                "date_resolution": dates.valeur,
                "technicien": technicien.valeur,
            }
        )
        bilan.retenues += 1
        journal.extend(notes)
    return retenues, journal, bilan


def _ecarter_doublon(
    ligne: dict[str, str],
    colonnes: list[str],
    empreintes: set[str],
    identifiants: set[str],
    identifiant: str,
    fichier: str,
    journal: list[dict],
    bilan: Bilan,
) -> bool:
    signature = "\x1f".join(ligne[colonne] for colonne in colonnes)
    if est_doublon(signature, empreintes):
        journal.append(
            _entree(
                fichier,
                identifiant,
                colonnes[0],
                identifiant,
                "Ligne identique à une ligne déjà traitée",
                "doublon",
            )
        )
        bilan.doublons += 1
        return True
    empreintes.add(signature)
    if identifiant in identifiants:
        journal.append(
            _entree(
                fichier,
                identifiant,
                colonnes[0],
                identifiant,
                "Identifiant déjà traité avec un contenu différent",
                "rejet",
            )
        )
        bilan.rejetees += 1
        return True
    identifiants.add(identifiant)
    return False


def _controler(
    controles: list[tuple[Resultat, str]],
    notes: list[dict],
    journal: list[dict],
    bilan: Bilan,
    fichier: str,
    identifiant: str,
) -> bool:
    for resultat, valeur_brute in controles:
        if not resultat.acceptee:
            journal.append(
                _entree(fichier, identifiant, resultat.colonne, valeur_brute, resultat.motif, "rejet")
            )
            bilan.rejetees += 1
            return False
        _noter(resultat, valeur_brute, notes, fichier, identifiant)
    return True


def _noter(resultat: Resultat, valeur_brute: str, notes: list[dict], fichier: str, identifiant: str) -> None:
    if resultat.normalisee and resultat.motif:
        notes.append(_entree(fichier, identifiant, resultat.colonne, valeur_brute, resultat.motif, "normalisation"))
    if resultat.avertissement and resultat.motif:
        notes.append(_entree(fichier, identifiant, resultat.colonne, valeur_brute, resultat.motif, "avertissement"))


def _entree(
    fichier: str,
    identifiant: str,
    colonne: str | None,
    valeur: object,
    motif: str | None,
    decision: str,
) -> dict[str, str]:
    return {
        "fichier": fichier,
        "identifiant": identifiant,
        "colonne": colonne or "",
        "valeur": "" if valeur is None else str(valeur),
        "motif": motif or "",
        "decision": decision,
    }


def inserer(session, modele, lignes: list[dict], cle: str) -> None:
    if not lignes:
        return
    requete = inserer_pg(modele.__table__).values(lignes).on_conflict_do_nothing(index_elements=[cle])
    session.execute(requete)


def ecrire_journal(lignes: list[dict], chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as fichier:
        redacteur = csv.DictWriter(fichier, fieldnames=COLONNES_JOURNAL)
        redacteur.writeheader()
        redacteur.writerows(lignes)


if __name__ == "__main__":
    main()
