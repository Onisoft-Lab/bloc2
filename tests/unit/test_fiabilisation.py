"""Cas nominal et rejet de chaque règle de fiabilisation."""

from datetime import datetime
from decimal import Decimal

from api.services.fiabilisation import (
    CibleNormalisee,
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

STATIONS = {"S001", "S002"}


def test_une_ligne_deja_vue_est_un_doublon():
    vues: set[str] = set()
    assert est_doublon("ligne-1", vues) is False
    vues.add("ligne-1")
    assert est_doublon("ligne-1", vues) is True


def test_velo_id_majuscule_accepte_et_minuscule_normalisee():
    valide = normaliser_velo_id("V1167")
    assert valide.acceptee is True
    assert valide.valeur == "V1167"
    assert valide.normalisee is False

    normalise = normaliser_velo_id("v1281")
    assert normalise.acceptee is True
    assert normalise.valeur == "V1281"
    assert normalise.normalisee is True

    assert normaliser_velo_id("V12").acceptee is False
    assert normaliser_velo_id("").acceptee is False


def test_identifiant_station_et_capacite():
    assert valider_identifiant_station("S001").valeur == "S001"
    minuscule = valider_identifiant_station("s001")
    assert minuscule.acceptee is True
    assert minuscule.valeur == "S001"
    assert minuscule.normalisee is True
    assert valider_identifiant_station("S0001").acceptee is False

    assert valider_capacite("15").valeur == 15
    assert valider_capacite("0").acceptee is False
    assert valider_capacite("-3").acceptee is False
    assert valider_capacite("abc").acceptee is False


def test_coordonnee_et_texte_obligatoire():
    assert valider_coordonnee("50.59932", "latitude").valeur == Decimal("50.59932")
    assert valider_coordonnee("abc", "longitude").acceptee is False
    assert valider_texte_obligatoire("Lille", "commune").valeur == "Lille"
    assert valider_texte_obligatoire("  ", "nom").acceptee is False


def test_date_et_horodatages():
    assert normaliser_date("2023-08-07").valeur.isoformat() == "2023-08-07"
    date_fr = normaliser_date("07/08/2023")
    assert date_fr.acceptee is True
    assert date_fr.normalisee is True
    assert date_fr.valeur.isoformat() == "2023-08-07"
    assert normaliser_date("2023/08/07").acceptee is False
    assert normaliser_date("").acceptee is False

    trajet = normaliser_horodatage_trajet("2026-08-24 08:39:56")
    assert trajet.acceptee is True
    assert trajet.normalisee is False
    francais = normaliser_horodatage_trajet("24/08/2026 11:01")
    assert francais.normalisee is True
    assert francais.valeur == datetime(2026, 8, 24, 11, 1)
    assert normaliser_horodatage_trajet("pas une date").acceptee is False

    incident = normaliser_horodatage_incident("2026-08-05 15:00")
    assert incident.acceptee is True
    assert incident.normalisee is False
    assert normaliser_horodatage_incident("").acceptee is False
    assert parser_horodatage_optionnel("", "date_resolution").valeur is None
    assert parser_horodatage_optionnel("n/a", "date_resolution").acceptee is False


def test_duree_strictement_positive():
    assert valider_duree_secondes("215").valeur == 215
    assert valider_duree_secondes("0").acceptee is False
    assert valider_duree_secondes("-120").acceptee is False
    assert valider_duree_secondes("abc").acceptee is False


def test_references_de_station():
    assert valider_station_depart("S001", STATIONS).valeur == "S001"
    assert valider_station_depart("", STATIONS).acceptee is False
    assert valider_station_depart("S999", STATIONS).acceptee is False

    assert valider_station_arrivee("", STATIONS).valeur is None
    assert valider_station_arrivee("S002", STATIONS).valeur == "S002"
    assert valider_station_arrivee("S999", STATIONS).acceptee is False


def test_type_usager_et_pseudonyme():
    assert normaliser_type_usager("abonne").valeur == "abonne"
    normalise = normaliser_type_usager("Occasionnel")
    assert normalise.valeur == "occasionnel"
    assert normalise.normalisee is True
    assert normaliser_type_usager("vip").acceptee is False

    assert valider_usager_ref("abonne", "Ued311b7d").valeur == "Ued311b7d"
    assert valider_usager_ref("occasionnel", "").valeur is None
    absent = valider_usager_ref("abonne", "")
    assert absent.acceptee is True
    assert absent.avertissement is True
    assert valider_usager_ref("occasionnel", "Ued311b7d").acceptee is False
    assert valider_usager_ref("abonne", "abc").acceptee is False


def test_statut_normalise_casse_et_espace():
    assert normaliser_statut("ouvert").valeur == "ouvert"
    assert normaliser_statut("ouvert").normalisee is False
    en_cours = normaliser_statut("En cours")
    assert en_cours.valeur == "en_cours"
    assert en_cours.normalisee is True
    assert normaliser_statut("RESOLU").valeur == "resolu"
    assert normaliser_statut("ferme").acceptee is False


def test_coherence_de_la_cible():
    velo = valider_coherence_cible("velo", "V0745", "", STATIONS)
    assert velo.valeur == CibleNormalisee("velo", "V0745", None)
    station = valider_coherence_cible("station", "", "S001", STATIONS)
    assert station.valeur == CibleNormalisee("station", None, "S001")
    assert valider_coherence_cible("velo", "V0745", "S001", STATIONS).acceptee is False
    assert valider_coherence_cible("velo", "VV", "", STATIONS).acceptee is False
    assert valider_coherence_cible("station", "V0745", "S001", STATIONS).acceptee is False
    assert valider_coherence_cible("station", "", "S999", STATIONS).acceptee is False
    assert valider_coherence_cible("velo", "", "", STATIONS).acceptee is False
    assert valider_coherence_cible("autre", "", "", STATIONS).acceptee is False


def test_coherence_des_dates_de_resolution():
    signalement = datetime(2026, 7, 23, 18, 0)
    resolution = datetime(2026, 7, 24, 6, 0)
    assert valider_coherence_dates("resolu", signalement, resolution).acceptee is True
    assert valider_coherence_dates("resolu", signalement, None).acceptee is False
    assert valider_coherence_dates("resolu", signalement, datetime(2026, 7, 22, 6, 0)).acceptee is False
    assert valider_coherence_dates("ouvert", signalement, resolution).acceptee is False
    assert valider_coherence_dates("en_cours", signalement, None).acceptee is True


def test_technicien_absent_signale_des_la_prise_en_charge():
    manque = avertir_technicien_absent("en_cours", "")
    assert manque.avertissement is True
    assert manque.acceptee is True
    assert avertir_technicien_absent("resolu", "  ").avertissement is True
    assert avertir_technicien_absent("ouvert", "").avertissement is False
    assert avertir_technicien_absent("en_cours", "A. Diallo").valeur == "A. Diallo"
