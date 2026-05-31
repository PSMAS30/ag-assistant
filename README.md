# AG Assistant — Transcription et synthese d assemblees generales

> Transformez vos enregistrements d assemblees generales en proces-verbaux structures et conformes au droit francais.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red)](https://streamlit.io)
[![Claude API](https://img.shields.io/badge/Claude-claude--opus--4--6-purple)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Demo live :** [ag-assistant.streamlit.app](https://ag-assistant.streamlit.app)

---

## Le probleme reel d une assemblee generale

Le PV n est qu une etape. Le vrai risque se situe tout au long du processus :

- Convocation envoyee trop tard ou incomplète
- Feuille de presence incomplete
- Quorum non verifie avant de voter
- Vote mal comptabilise ou sans base legale
- Resolutions contestees mois plus tard
- PV non conforme ou non archive

**AG Assistant** securise ce processus de bout en bout.

---

## Presentation

**AG Assistant** est un outil Python qui combine transcription audio locale et intelligence artificielle pour generer automatiquement des proces-verbaux d assemblees generales conformes aux standards juridiques francais.

**Cibles :** PME, associations loi 1901, coproprietes, syndics, cabinets juridiques

**Differenciateur :** specialisation droit francais + traçabilite audio + memoire des AG precedentes

---

## Fonctionnalites

### Transcription locale
- Transcription audio 100% locale via **faster-whisper** (aucune donnee envoyee dans le cloud)
- Formats supportes : MP3, WAV, M4A, OGG, FLAC
- Modeles Whisper au choix : tiny → large-v3
- Segments horodates affiches dans l interface

### Identification des locuteurs (diarization)
- Detection automatique de **qui parle et quand** via **pyannote.audio**
- Renommage interactif des locuteurs (SPEAKER_00 → "M. Dupont")
- Timeline coloree par intervenant
- Fonctionne avec 2 a 6 locuteurs distincts

### Analyse juridique par IA
- Extraction structuree par **Claude** : participants, ordre du jour, resolutions, votes, quorum
- Regles metier francaises integrees :
  - Copropriete : art. 24, 25, 26 (loi 10 juillet 1965)
  - Association loi 1901 : majorites, quorum selon statuts
  - SAS / SARL : regles selon forme juridique
- Verification automatique des mentions obligatoires du PV
- Alertes conformite + recommandations

### Sources et traçabilite
- Chaque resolution est liee a son horodatage audio exact (`00:42:18 → 00:45:01`)
- Niveau de confiance par section : Participants / Votes / Quorum / Convocation / ODJ
- Sections incertaines identifiees et signalee

### Generation du PV
- Trois templates selon le type d entite (copropriete / association / PME SAS/SARL)
- Export **PDF**, **Word (.docx)**, **TXT**
- PV editable dans l interface avant export
- Disclaimer IA + niveau de confiance inclus dans chaque document

### Convocation
- Generation d un document de convocation conforme par type d entite
- Export PDF et Word
- Mentions legales obligatoires pre-remplies

### Feuille de presence
- Generation d une feuille de presence pre-remplie depuis l analyse
- Export PDF et Word

### Historique et memoire
- Sauvegarde automatique de chaque AG analysee
- Audit trail horodate de toutes les actions
- Comparaison N vs N-1 : evolution des resolutions, votes, quorum d une AG a l autre
- Export / import de l historique (JSON zip)

### Q&A sur l AG
- Posez des questions en langage naturel sur n importe quelle AG analysee
- Reponses basees sur la transcription + l analyse structuree

---

## Deux modes d utilisation

| Fonctionnalite | Demo en ligne (Streamlit Cloud) | Installation locale |
|----------------|--------------------------------|---------------------|
| Upload audio + transcription | ❌ | ✅ |
| Diarization (identification locuteurs) | ❌ | ✅ |
| 3 AG fictives (mode demo) | ✅ | ✅ |
| Analyse Claude (avec cle API) | ✅ | ✅ |
| PV / Convocation / Feuille de presence | ✅ | ✅ |
| Historique persistant | ❌ ephemere | ✅ sur disque |

> **Streamlit Cloud** = tester les fonctionnalites IA sans installation
> **Installation locale** = traiter vos vrais enregistrements audio

---

## Demarrage rapide

### Prerequis
- Python 3.10+
- pip

### Option A — Demo en ligne (sans installation)

👉 [ag-assistant.streamlit.app](https://ag-assistant.streamlit.app)

Entrez votre cle API Anthropic dans la sidebar → toutes les fonctions IA disponibles.
La transcription audio necessite l installation locale (Option B).

---

### Option B — Installation locale complete (avec transcription audio)

```bash
git clone https://github.com/PSMAS30/ag-assistant.git
cd ag-assistant

# Dependances de base
pip install -r requirements-local.txt

# PyTorch CPU (pour la transcription et la diarization)
pip install torch==2.6.0+cpu torchaudio==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu

# Lancer l application
streamlit run app.py
```

L application s ouvre sur `http://localhost:8501`

### Configuration (installation locale)

```bash
cp .env.example .env
# Editer .env et ajouter vos cles
```

Contenu du `.env` :
```
ANTHROPIC_API_KEY=sk-ant-...   # Requis pour l analyse et la generation de PV
HF_TOKEN=hf_...                 # Requis pour la diarization (optionnel)
```

**Obtenir les cles :**
- Cle Anthropic : [console.anthropic.com](https://console.anthropic.com)
- Token HuggingFace : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
  - Accepter les CGU : [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

---

## Mode demo (sans cle API)

L application inclut 3 assemblees fictives pour tester sans audio et sans cle API :
- **Copropriete Les Acacias** — AG annuelle avec travaux (art. 24/25)
- **Association Sportive Elan Vitry** — AGE modification statuts
- **SAS Innov Tech** — AGO approbation comptes, affectation resultat

---

## Architecture

```
ag-assistant/
+-- app.py                  Interface Streamlit (6 onglets)
+-- transcriber.py          Transcription audio + diarization
+-- analyzer.py             Analyse Claude → JSON structure
+-- pv_generator.py         Generation PV texte + PDF
+-- word_generator.py       Generation PV Word (.docx)
+-- convocation_generator.py Generation convocations
+-- presence_generator.py   Generation feuilles de presence
+-- historique_manager.py   Historique AG + audit trail + comparaison N/N-1
+-- prompts.py              System prompts (v1 — original)
+-- prompts_v2.py           Prompts enrichis conformite legale + sources + confiance
+-- demo_data.py            3 AG fictives pour la demo
+-- requirements.txt        Installation cloud (sans transcription)
+-- requirements-local.txt  Installation locale complete
+-- .env.example
+-- historique/             AG sauvegardees (local — non versionnees)
+-- tests/
    +-- fixtures/           Reponses Claude simulees (tests sans API)
    +-- test_analyzer.py
    +-- test_pv_generator.py
    +-- test_word_generator.py
    +-- test_transcriber.py
    +-- test_demo_data.py
    +-- test_historique_manager.py
    +-- test_convocation_generator.py
    +-- test_presence_generator.py
```

---

## Tests

```bash
pytest tests/ -v
```

43+ tests — 100% sans appel API grace aux fixtures JSON.

---

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Interface | Streamlit |
| Transcription | faster-whisper (CPU, local) |
| Diarization | pyannote.audio 3.x |
| LLM | Claude API — claude-opus-4-6 |
| Export PDF | fpdf2 |
| Export Word | python-docx |
| Tests | pytest + mocks + fixtures JSON |

---

## Avertissement legal

AG Assistant est un **outil d assistance**, pas une autorite legale.

Chaque document genere inclut un disclaimer explicite :
> *Document genere par assistance IA. Doit etre relu, corrige et valide par les parties avant toute valeur juridique.*

L outil ne remplace pas un conseil juridique. En cas de doute sur la validite d une resolution ou d un quorum, consultez un professionnel du droit.

La signature electronique n est pas supportee dans cette version.

---

## Contribution

Issues et pull requests bienvenus.

---

## Licence

MIT — voir [LICENSE](LICENSE)
