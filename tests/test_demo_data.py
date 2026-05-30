"""Tests unitaires pour demo_data.py"""
import pytest
from demo_data import get_demo, list_demos, DEMOS


def test_list_demos_retourne_liste_non_vide():
    demos = list_demos()
    assert isinstance(demos, list)
    assert len(demos) >= 3


def test_list_demos_contient_cles_et_labels():
    for d in list_demos():
        assert "key" in d
        assert "label" in d


def test_get_demo_copropriete():
    d = get_demo("copropriete")
    assert "transcription" in d
    assert "metadata" in d
    assert d["metadata"]["type"] == "copropriete"
    assert len(d["transcription"]) > 100


def test_get_demo_association():
    d = get_demo("association")
    assert d["metadata"]["type"] == "association"


def test_get_demo_pme():
    d = get_demo("pme")
    assert d["metadata"]["type"] == "pme"


def test_get_demo_cle_invalide_leve_valueerror():
    with pytest.raises(ValueError, match="Démo inconnue"):
        get_demo("inexistant")


def test_toutes_demos_ont_transcription_non_vide():
    for key in DEMOS:
        d = get_demo(key)
        assert d["transcription"].strip() != ""
