"""
test_pv_generator.py — Tests pv_generator.py via fixtures (aucun appel API reel)
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _charger_fixture(nom: str) -> dict:
    with open(FIXTURES_DIR / nom, encoding="utf-8") as f:
        return json.load(f)


# ── Tests pv_demo (sans API) ─────────────────────────────────────────────────

def test_pv_demo_copropriete_retourne_string():
    """pv_demo retourne une chaine non vide pour la fixture copropriete."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    resultat = pv_generator.pv_demo(fixture)
    assert isinstance(resultat, str)
    assert len(resultat) > 100


def test_pv_demo_contient_entite():
    """Le PV demo contient le nom de l entite."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    pv = pv_generator.pv_demo(fixture)
    assert "Acacias" in pv


def test_pv_demo_contient_resolutions():
    """Le PV demo mentionne les resolutions."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    pv = pv_generator.pv_demo(fixture)
    assert "RESOLUTION" in pv.upper()


def test_pv_demo_association():
    """pv_demo fonctionne avec la fixture association."""
    import pv_generator
    fixture = _charger_fixture("analyse_association.json")
    pv = pv_generator.pv_demo(fixture)
    assert "Elan Vitry" in pv or "association" in pv.lower()


def test_pv_demo_pme():
    """pv_demo fonctionne avec la fixture PME."""
    import pv_generator
    fixture = _charger_fixture("analyse_pme.json")
    pv = pv_generator.pv_demo(fixture)
    assert "Innov" in pv


def test_pv_demo_quorum_atteint():
    """Le PV demo affiche OUI pour quorum atteint."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    pv = pv_generator.pv_demo(fixture)
    assert "OUI" in pv


def test_pv_demo_contient_disclaimer():
    """Le PV demo contient le disclaimer IA."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    pv = pv_generator.pv_demo(fixture)
    assert "provisoire" in pv.lower() or "demo" in pv.lower()


# ── Tests generer_pv_texte (avec mock Claude) ────────────────────────────────

def test_generer_pv_texte_avec_mock():
    """generer_pv_texte retourne le texte genere par Claude (mock)."""
    import pv_generator
    fixture = _charger_fixture("analyse_copropriete.json")
    pv_attendu = "PROCES-VERBAL\nCopropriete Les Acacias\nAdopte."
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=pv_attendu)]
    mock_client.messages.create.return_value = mock_message
    with patch("pv_generator.anthropic.Anthropic", return_value=mock_client):
        resultat = pv_generator.generer_pv_texte(fixture, "fake-api-key")
    assert resultat == pv_attendu


def test_generer_pv_utilise_bon_template():
    """generer_pv_texte utilise le template correspondant au type_ag."""
    import pv_generator
    from prompts_v2 import get_template_pv
    fixture = _charger_fixture("analyse_copropriete.json")
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="PV copropriete")]
    mock_client.messages.create.return_value = mock_message
    with patch("pv_generator.anthropic.Anthropic", return_value=mock_client):
        pv_generator.generer_pv_texte(fixture, "fake")
    # Verifier que le system prompt utilise est bien celui de la copropriete
    call_kwargs = mock_client.messages.create.call_args
    system_utilise = call_kwargs[1].get("system") or call_kwargs[0][3] if call_kwargs[0] else call_kwargs[1]["system"]
    assert "copropriete" in system_utilise.lower() or "1965" in system_utilise


# ── Tests export PDF ─────────────────────────────────────────────────────────

def test_exporter_pdf_cree_fichier():
    """exporter_pv_pdf cree bien un fichier PDF sur le disque."""
    import pv_generator
    texte = "PROCES-VERBAL\nTest de generation PDF.\nAdopte a l unanimite."
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        chemin = tmp.name
    try:
        pv_generator.exporter_pv_pdf(texte, chemin)
        assert os.path.exists(chemin)
        assert os.path.getsize(chemin) > 0
    finally:
        if os.path.exists(chemin):
            os.unlink(chemin)


def test_exporter_pdf_contenu_non_vide():
    """Le PDF genere a une taille raisonnable (> 1 Ko)."""
    import pv_generator
    texte = "\n".join([f"Ligne {i} du PV de test pour verification." for i in range(30)])
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        chemin = tmp.name
    try:
        pv_generator.exporter_pv_pdf(texte, chemin)
        assert os.path.getsize(chemin) > 1024
    finally:
        if os.path.exists(chemin):
            os.unlink(chemin)
