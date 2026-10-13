"""Le classement des CSV respecte l'équation importées + rejetées + doublons."""

from pathlib import Path

from scripts.importer import traiter_incidents, traiter_stations, traiter_trajets

DOSSIER = Path(__file__).resolve().parents[2] / "data"


def test_volumes_des_trois_exports():
    from scripts.importer import lire_csv
    from scripts.importer import COLONNES_INCIDENT, COLONNES_STATION, COLONNES_TRAJET

    stations, _, bilan_stations = traiter_stations(lire_csv(DOSSIER / "stations.csv", COLONNES_STATION))
    connues = {ligne["station_id"] for ligne in stations}
    _, _, bilan_trajets = traiter_trajets(lire_csv(DOSSIER / "trajets.csv", COLONNES_TRAJET), connues)
    _, _, bilan_incidents = traiter_incidents(
        lire_csv(DOSSIER / "incidents.csv", COLONNES_INCIDENT),
        connues,
    )

    assert (bilan_stations.retenues, bilan_stations.rejetees, bilan_stations.doublons) == (120, 0, 0)
    assert (bilan_trajets.retenues, bilan_trajets.rejetees, bilan_trajets.doublons) == (2002, 16, 12)
    assert (bilan_incidents.retenues, bilan_incidents.rejetees, bilan_incidents.doublons) == (177, 3, 0)
    for bilan in (bilan_stations, bilan_trajets, bilan_incidents):
        assert bilan.retenues + bilan.rejetees + bilan.doublons == bilan.lues
