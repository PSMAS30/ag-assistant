"""Tests unitaires pour transcriber.py"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_format_invalide_leve_valueerror(tmp_path):
    faux_fichier = tmp_path / "audio.xyz"
    faux_fichier.write_text("contenu")
    from transcriber import transcrire_audio
    with pytest.raises(ValueError, match="Format non support"):
        transcrire_audio(str(faux_fichier))


def test_fichier_inexistant_leve_filenotfounderror():
    from transcriber import transcrire_audio
    with pytest.raises(FileNotFoundError):
        transcrire_audio("/chemin/inexistant/audio.mp3")


def test_formats_acceptes_contient_mp3():
    from transcriber import FORMATS_ACCEPTES
    assert ".mp3" in FORMATS_ACCEPTES
    assert ".wav" in FORMATS_ACCEPTES
    assert ".m4a" in FORMATS_ACCEPTES


def test_transcrire_audio_retourne_dict_structure(tmp_path):
    faux_audio = tmp_path / "test.mp3"
    faux_audio.write_bytes(b"faux audio")

    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.start = 0.0
    mock_segment.end = 5.0
    mock_segment.text = " Bonjour à tous."
    mock_info = MagicMock()
    mock_info.language = "fr"
    mock_info.duration = 5.0
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    with patch("faster_whisper.WhisperModel", return_value=mock_model):
        from transcriber import transcrire_audio
        result = transcrire_audio(str(faux_audio))

    assert "texte" in result
    assert "segments" in result
    assert "langue" in result
    assert result["texte"] == "Bonjour à tous."
    assert result["langue"] == "fr"
