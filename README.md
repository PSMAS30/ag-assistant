# AG Assistant — Transcription et synthese d assemblees generales

> Transformez vos enregistrements d assemblees generales en proces-verbaux structures et conformes au droit francais.

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57-red)](https://streamlit.io)
[![Claude API](https://img.shields.io/badge/Claude-claude--opus--4--6-purple)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Presentation

**AG Assistant** est un outil Python qui combine transcription audio locale et intelligence artificielle pour generer automatiquement des proces-verbaux d assemblees generales conformes aux standards juridiques francais.

**Cibles :** PME, associations loi 1901, coproprietes, syndics, cabinets juridiques

**Differenciateur :** specialisation droit francais (loi 10 juillet 1965, loi 1901, code commerce) vs outils generiques

---

## Fonctionnalites

### Transcription
- Transcription audio 100% locale via **faster-whisper** (aucun cloud, donnees protegees)
- Formats supportes : MP3, WAV, M4A, OGG, FLAC
- Modeles Whisper au choix : tiny, base, small, medium, large-v2, large-v3
- Segments horodates affichés dans l interface

### Identification des locuteurs (diarization)
- Detection automatique de **qui parle et quand** via **pyannote.audio**
- Renommage interactif des locuteurs (SPEAKER_00 -> "M. Dupont")
- Timeline coloree par intervenant
- Fonctionne avec 2 a 6 locuteurs distincts

### Analyse juridique
- Extraction structuree par **Claude** : participants, ordre du jour, resolutions, votes, quorum
- Regles metier francaises integrees :
  - Copropriete : art. 24, 25, 26 (loi 10 juillet 1965)
  - Association loi 1901 : majorites, quorum selon statuts
  - SAS / SARL : regles selon forme juridique
- Verification automatique des mentions obligatoires
- Alertes conformite + recommandations
- Niveau de confiance par section

### Generation du PV
- Trois templates selon le type d entite (copropriete / association / PME)
- Export **PDF**, **Word (.docx)**, **TXT**
- PV editable dans l interface avant export
- Disclaimer IA inclus dans chaque document

### Q&A sur l AG
- Posez des questions en langage naturel sur n importe quelle AG analysee
- Base sur la transcription + l analyse structuree

---

## Demarrage rapide

### Prerequis
- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/PSMAS30/ag-assistant.git
cd ag-assistant
pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Editer .env et ajouter vos cles
```

Contenu du `.env` :
```
ANTHROPIC_API_KEY=sk-ant-...   # Requis pour l analyse
HF_TOKEN=hf_...                 # Requis pour la diarization
```

**Obtenir les cles :**
- Cle Anthropic : [console.anthropic.com](https://console.anthropic.com)
- Token HuggingFace : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
  - Puis accepter les CGU : [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)

### Lancement

```bash
streamlit run app.py
```

L application s ouvre sur `http://localhost:8501`

---

## Mode demo (sans cle API)

L application inclut 3 assemblees fictives pour tester sans audio et sans cle API :
- **Copropriete Les Acacias** — AG annuelle avec travaux
- **Association Sportive Elan Vitry** — AGE modification statuts
- **SAS Innov Tech** — AGO approbation comptes

---

## Architecture

```
ag-assistant/
+-- app.py              Interface Streamlit (4 onglets)
+-- transcriber.py      Transcription audio + diarization
+-- analyzer.py         Analyse Claude -> JSON structure
+-- pv_generator.py     Generation PV texte + PDF
+-- word_generator.py   Generation PV Word (.docx)
+-- prompts.py          System prompts (v1)
+-- prompts_v2.py       Prompts enrichis conformite legale
+-- demo_data.py        3 AG fictives pour la demo
+-- requirements.txt
+-- .env.example
+-- tests/
    +-- fixtures/       Reponses Claude simulees (tests sans API)
    +-- test_analyzer.py
    +-- test_pv_generator.py
    +-- test_word_generator.py
    +-- test_transcriber.py
    +-- test_demo_data.py
```

---

## Tests

```bash
pytest tests/ -v
```

37 tests — 100% sans appel API grace aux fixtures JSON.

---

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Interface | Streamlit |
| Transcription | faster-whisper (CPU) |
| Diarization | pyannote.audio 3.x |
| LLM | Claude API (Anthropic) |
| Export PDF | fpdf2 |
| Export Word | python-docx |
| Tests | pytest + mocks |

---

## Avertissement legal

AG Assistant est un **outil d assistance**, pas une autorite legale.

Chaque document genere inclut un disclaimer explicite :
> *Document genere par assistance IA. Doit etre relu, corrige et valide par les parties avant toute valeur juridique.*

L outil ne remplace pas un conseil juridique. En cas de doute sur la validite d une resolution ou d un quorum, consultez un professionnel du droit.

---

## Contribution

Issues et pull requests bienvenus.

---

## Licence

MIT — voir [LICENSE](LICENSE)
