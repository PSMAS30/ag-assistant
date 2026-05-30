"""
test_analyzer.py — Tests analyzer.py via mocks (aucun appel API reel)
Les fixtures JSON simulent les reponses de Claude.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _charger_fixture(nom: str) -> dict:
    """Charge un fichier fixture JSON."""
    with open(FIXTURES_DIR / nom, encoding="utf-8") as f:
        return json.load(f)


def _mock_claude(fixture_dict: dict):
    """Cree un mock anthropic.Anthropic retournant la fixture en JSON."""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(fixture_dict, ensure_ascii=False))]
    mock_client.messages.create.return_value = mock_message
    return mock_client


# ── Tests analyser_transcription ────────────────────────────────────────────

def test_analyser_retourne_dict():
    """analyser_transcription retourne bien un dict."""
    import analyzer
    fixture = _charger_fixture("analyse_copropriete.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("transcription test", "fake-api-key")
    assert isinstance(resultat, dict)


def test_analyser_copropriete_type_ag():
    """type_ag est bien copropriete pour la fixture copropriete."""
    import analyzer
    fixture = _charger_fixture("analyse_copropriete.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("transcription copropriete", "fake")
    assert resultat.get("type_ag") == "copropriete"


def test_analyser_association_quorum_atteint():
    """Le quorum est marque atteint pour la fixture association."""
    import analyzer
    fixture = _charger_fixture("analyse_association.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("transcription asso", "fake")
    assert resultat["participants"]["quorum_atteint"] is True


def test_analyser_pme_4_resolutions():
    """La fixture PME contient bien 4 resolutions."""
    import analyzer
    fixture = _charger_fixture("analyse_pme.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("transcription pme", "fake")
    assert len(resultat.get("resolutions", [])) == 4


def test_analyser_json_invalide_leve_valueerror():
    """Si Claude renvoie du texte non-JSON, ValueError est leve."""
    import analyzer
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Voici mon analyse : blabla")]
    mock_client.messages.create.return_value = mock_message
    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(ValueError, match="JSON valide"):
            analyzer.analyser_transcription("texte", "fake")


def test_analyser_nettoie_balises_markdown():
    """Les balises ```json ... ``` sont correctement retirees."""
    import analyzer
    fixture = _charger_fixture("analyse_copropriete.json")
    contenu_markdown = "```json\n" + json.dumps(fixture) + "\n```"
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=contenu_markdown)]
    mock_client.messages.create.return_value = mock_message
    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        resultat = analyzer.analyser_transcription("texte", "fake")
    assert isinstance(resultat, dict)
    assert resultat.get("type_ag") == "copropriete"


def test_analyser_copropriete_resolutions_statut():
    """Les resolutions copropriete ont un statut adoptee ou rejetee."""
    import analyzer
    fixture = _charger_fixture("analyse_copropriete.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("copro", "fake")
    statuts_valides = {"adoptée", "rejetée", "nulle", "reportée", "retirée"}
    for r in resultat.get("resolutions", []):
        assert r.get("statut") in statuts_valides, f"Statut invalide : {r.get('statut')}"


def test_analyser_meta_version():
    """Le champ meta.version est present et vaut 2.0."""
    import analyzer
    fixture = _charger_fixture("analyse_copropriete.json")
    with patch("analyzer.anthropic.Anthropic", return_value=_mock_claude(fixture)):
        resultat = analyzer.analyser_transcription("texte", "fake")
    assert resultat.get("meta", {}).get("version") == "2.0"


def test_poser_question_retourne_string():
    """poser_question retourne bien une string."""
    import analyzer
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="La resolution 3 a ete adoptee.")]
    mock_client.messages.create.return_value = mock_message
    with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
        reponse = analyzer.poser_question("transcription", {}, "Qui a vote contre ?", "fake")
    assert isinstance(reponse, str)
    assert len(reponse) > 0
