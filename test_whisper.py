"""
test_whisper.py — Vérifie que faster-whisper est bien installé et fonctionnel.
Lance avec : python test_whisper.py
"""

import wave
import struct
import os
import tempfile

print("🔍 Test de faster-whisper...")

# Étape 1 : créer un fichier WAV de 2 secondes (silence)
# On utilise uniquement la bibliothèque standard Python — pas de dépendance supplémentaire.
tmp_wav = tempfile.mktemp(suffix=".wav")
sample_rate = 16000
duration_seconds = 2
n_samples = sample_rate * duration_seconds

with wave.open(tmp_wav, "w") as f:
    f.setnchannels(1)        # mono
    f.setsampwidth(2)        # 16 bits
    f.setframerate(sample_rate)
    f.writeframes(struct.pack("<" + "h" * n_samples, *([0] * n_samples)))

print(f"  ✅ Fichier audio temporaire créé : {tmp_wav}")

# Étape 2 : charger le modèle et transcrire
try:
    from faster_whisper import WhisperModel

    print("  ⏳ Chargement du modèle medium (déjà en cache si téléchargé)...")
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    print("  ✅ Modèle chargé")

    print("  ⏳ Transcription du fichier de test...")
    segments, info = model.transcribe(tmp_wav, language="fr")
    texte = " ".join(s.text for s in segments).strip()

    print(f"  ✅ Transcription réussie — langue détectée : {info.language}")
    print(f"  📝 Texte transcrit : '{texte}' (vide = normal pour un silence)")
    print()
    print("✅ faster-whisper est opérationnel. Prêt pour l'étape suivante.")

except ImportError:
    print("  ❌ faster-whisper n'est pas installé.")
    print("  → Lance : pip install faster-whisper")

except Exception as e:
    print(f"  ❌ Erreur : {e}")

finally:
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)
