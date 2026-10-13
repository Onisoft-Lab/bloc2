"""Transitions de statut autorisées."""

from api.services.incidents import transition_autorisee


def test_seules_trois_transitions_sont_autorisees():
    assert transition_autorisee("ouvert", "en_cours") is True
    assert transition_autorisee("ouvert", "resolu") is True
    assert transition_autorisee("en_cours", "resolu") is True
    assert transition_autorisee("en_cours", "ouvert") is False
    assert transition_autorisee("resolu", "ouvert") is False
    assert transition_autorisee("resolu", "en_cours") is False
    assert transition_autorisee("ouvert", "ouvert") is False
