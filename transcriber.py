"""
transcriber.py — Transcription audio via faster-whisper (100% local, sans cloud)
              + Diarization via pyannote.audio (identification des locuteurs)
"""

import os
from pathlib import Path


FORMATS_ACCEPTES = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".webm"}
MODELES_DISPONIBLES = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
MODELE_DEFAUT = "medium"


def transcrire_audio(chemin_audio: str, modele: str = MODELE_DEFAUT, langue: str = "fr") -> dict:
    """
    Transcrit un fichier audio en texte via faster-whisper.

    Args:
        chemin_audio: Chemin vers le fichier audio
        modele: Modele Whisper a utiliser (defaut: medium)
        langue: Langue de la transcription (defaut: fr)

    Returns:
        dict: {
            "texte": str,           # Transcription complete
            "segments": list,       # Segments horodates [{debut, fin, texte}]
            "langue": str,          # Langue detectee
            "duree_secondes": float # Duree totale
        }

    Raises:
        FileNotFoundError: Si le fichier audio n existe pas
        ValueError: Si le format n est pas supporte
    """
    from faster_whisper import WhisperModel

    chemin = Path(chemin_audio)
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {chemin_audio}")

    if chemin.suffix.lower() not in FORMATS_ACCEPTES:
        raise ValueError(
            f"Format non supporte : {chemin.suffix}. "
            f"Formats acceptes : {', '.join(FORMATS_ACCEPTES)}"
        )

    model = WhisperModel(modele, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(
        chemin_audio,
        language=langue,
        beam_size=5,
        vad_filter=True,
    )

    segments = []
    texte_complet = []

    for segment in segments_iter:
        segments.append({
            "debut": round(segment.start, 2),
            "fin": round(segment.end, 2),
            "texte": segment.text.strip(),
        })
        texte_complet.append(segment.text.strip())

    return {
        "texte": " ".join(texte_complet),
        "segments": segments,
        "langue": info.language,
        "duree_secondes": round(info.duration, 2) if hasattr(info, "duration") else None,
    }


def transcrire_avec_diarization(
    chemin_audio: str,
    modele: str = MODELE_DEFAUT,
    langue: str = "fr",
    hf_token: str = None,
    nb_locuteurs: int = None,
) -> dict:
    """
    Transcrit un fichier audio ET identifie les locuteurs (qui parle quand).
    Combine faster-whisper (transcription) + pyannote.audio (diarization).

    Args:
        chemin_audio: Chemin vers le fichier audio
        modele: Modele Whisper a utiliser
        langue: Langue de la transcription
        hf_token: Token HuggingFace (ou None pour lire depuis HF_TOKEN env var)
        nb_locuteurs: Nombre de locuteurs si connu (None = detection automatique)

    Returns:
        dict: {
            "texte": str,                    # Transcription complete (texte brut)
            "segments": list,                # Segments Whisper sans locuteur
            "segments_diarises": list,       # Segments alignes avec locuteur
            "locuteurs": list,               # Liste des locuteurs detectes
            "langue": str,
            "duree_secondes": float
        }

    Raises:
        FileNotFoundError: Si le fichier audio n existe pas
        ValueError: Si le format n est pas supporte ou token HF manquant
        ImportError: Si pyannote.audio n est pas installe
    """
    from dotenv import load_dotenv
    load_dotenv()

    token = hf_token or os.getenv("HF_TOKEN", "")
    if not token:
        raise ValueError(
            "Token HuggingFace requis pour la diarization. "
            "Definir HF_TOKEN dans .env ou passer hf_token= en parametre."
        )

    chemin = Path(chemin_audio)
    if not chemin.exists():
        raise FileNotFoundError(f"Fichier audio introuvable : {chemin_audio}")
    if chemin.suffix.lower() not in FORMATS_ACCEPTES:
        raise ValueError(f"Format non supporte : {chemin.suffix}")

    # ── Etape 1 : Transcription Whisper ──────────────────────────────────────
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(modele, device="cpu", compute_type="int8")
    segments_iter, info = whisper_model.transcribe(
        chemin_audio,
        language=langue,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,  # Timestamps mot par mot pour alignement precis
    )

    segments_whisper = []
    texte_complet = []
    for segment in segments_iter:
        segments_whisper.append({
            "debut": round(segment.start, 2),
            "fin": round(segment.end, 2),
            "texte": segment.text.strip(),
        })
        texte_complet.append(segment.text.strip())

    # ── Etape 2 : Diarization pyannote ───────────────────────────────────────
    try:
        from pyannote.audio import Pipeline
        import torch
    except ImportError:
        raise ImportError(
            "pyannote.audio n est pas installe. "
            "Lancez : pip install pyannote.audio"
        )

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=token,
    )

    # Inference diarization
    diarization_kwargs = {}
    if nb_locuteurs:
        diarization_kwargs["num_speakers"] = nb_locuteurs

    diarization = pipeline(chemin_audio, **diarization_kwargs)

    # ── Etape 3 : Alignement Whisper + pyannote ───────────────────────────────
    # Pour chaque segment Whisper, trouver le locuteur dominant
    def trouver_locuteur(debut: float, fin: float, diarization) -> str:
        """Retourne le locuteur qui parle le plus pendant l intervalle [debut, fin]."""
        durees = {}
        for segment, _, locuteur in diarization.itertracks(yield_label=True):
            overlap_debut = max(debut, segment.start)
            overlap_fin = min(fin, segment.end)
            if overlap_fin > overlap_debut:
                durees[locuteur] = durees.get(locuteur, 0) + (overlap_fin - overlap_debut)
        if not durees:
            return "Intervenant non identifie"
        return max(durees, key=durees.get)

    segments_diarises = []
    locuteurs_detectes = set()

    for seg in segments_whisper:
        locuteur = trouver_locuteur(seg["debut"], seg["fin"], diarization)
        locuteurs_detectes.add(locuteur)
        segments_diarises.append({
            "debut": seg["debut"],
            "fin": seg["fin"],
            "locuteur": locuteur,
            "texte": seg["texte"],
        })

    return {
        "texte": " ".join(texte_complet),
        "segments": segments_whisper,
        "segments_diarises": segments_diarises,
        "locuteurs": sorted(list(locuteurs_detectes)),
        "langue": info.language,
        "duree_secondes": round(info.duration, 2) if hasattr(info, "duration") else None,
    }


def renommer_locuteurs(segments_diarises: list, mapping: dict) -> list:
    """
    Renomme les locuteurs dans les segments diarises.
    Exemple : {"SPEAKER_00": "Maitre Lefebvre", "SPEAKER_01": "Mme Petit"}

    Args:
        segments_diarises: Liste de segments [{debut, fin, locuteur, texte}]
        mapping: Dict {nom_technique -> nom_affiche}

    Returns:
        list: Segments avec locuteurs renommes
    """
    return [
        {**seg, "locuteur": mapping.get(seg["locuteur"], seg["locuteur"])}
        for seg in segments_diarises
    ]


def segments_diarises_vers_texte(segments_diarises: list) -> str:
    """
    Convertit des segments diarises en texte formate :
    [SPEAKER_00 - 00:32] Bonjour a tous...
    [SPEAKER_01 - 01:15] Je suis d accord...
    """
    lignes = []
    for seg in segments_diarises:
        debut = seg.get("debut", 0)
        m, s = divmod(int(debut), 60)
        ts = f"{m:02d}:{s:02d}"
        loc = seg.get("locuteur", "?")
        texte = seg.get("texte", "")
        lignes.append(f"[{loc} - {ts}] {texte}")
    return "\n".join(lignes)


def sauvegarder_transcription(resultat: dict, chemin_sortie: str) -> None:
    """Sauvegarde la transcription dans un fichier texte."""
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(resultat["texte"])
