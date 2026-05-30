"""
test_historique_manager.py — Tests historique_manager.py (sans API)
"""

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _charger_fixture(nom):
    with open(FIXTURES_DIR / nom, encoding="utf-8") as f:
        return json.load(f)


def test_sauvegarder_et_lister(tmp_path, monkeypatch):
    """Sauvegarde une AG et verifie qu elle apparait dans la liste."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    fixture = _charger_fixture("analyse_copropriete.json")
    chemin = historique_manager.sauvegarder_ag(fixture, pv_texte="PV de test")
    assert Path(chemin).exists()
    ag_list = historique_manager.lister_ag()
    assert len(ag_list) == 1
    assert "Acacias" in ag_list[0]["entite"]


def test_charger_ag(tmp_path, monkeypatch):
    """Charge une AG sauvegardee et verifie le contenu."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    fixture = _charger_fixture("analyse_association.json")
    chemin = historique_manager.sauvegarder_ag(fixture, pv_texte="PV asso")
    entree = historique_manager.charger_ag(chemin)
    assert entree["pv_texte"] == "PV asso"
    assert entree["analyse"]["type_ag"] == "association"


def test_supprimer_ag(tmp_path, monkeypatch):
    """Supprime une AG et verifie qu elle disparait de la liste."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    fixture = _charger_fixture("analyse_pme.json")
    chemin = historique_manager.sauvegarder_ag(fixture)
    assert historique_manager.nb_ag_sauvegardees() == 1
    historique_manager.supprimer_ag(chemin)
    assert historique_manager.nb_ag_sauvegardees() == 0


def test_audit_trail(tmp_path, monkeypatch):
    """L audit trail enregistre les actions."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    fixture = _charger_fixture("analyse_copropriete.json")
    chemin = historique_manager.sauvegarder_ag(fixture)
    historique_manager.ajouter_action_audit(chemin, "pdf_exporte", "proces_verbal.pdf")
    entree = historique_manager.charger_ag(chemin)
    actions = [a["action"] for a in entree["meta_historique"]["audit_trail"]]
    assert "analyse_sauvegardee" in actions
    assert "pdf_exporte" in actions


def test_nb_ag_sauvegardees(tmp_path, monkeypatch):
    """nb_ag_sauvegardees retourne le bon compte."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    assert historique_manager.nb_ag_sauvegardees() == 0
    for nom in ["analyse_copropriete.json", "analyse_association.json", "analyse_pme.json"]:
        historique_manager.sauvegarder_ag(_charger_fixture(nom))
    assert historique_manager.nb_ag_sauvegardees() == 3


def test_historique_vide(tmp_path, monkeypatch):
    """lister_ag retourne liste vide si aucune AG."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    assert historique_manager.lister_ag() == []
