"""
analyzer.py — Analyse une transcription AG via Claude et retourne un JSON structuré
"""

import json
import anthropic
from prompts_v2 import SYSTEM_ANALYSE_AG_V2 as SYSTEM_ANALYSE_AG, SYSTEM_QA_AG_V2 as SYSTEM_QA_AG


def analyser_transcription(transcription: str, api_key: str) -> dict:
    """
    Envoie la transcription à Claude et retourne le JSON structuré de l'AG.

    Args:
        transcription: Texte brut de la transcription
        api_key: Clé API Anthropic

    Returns:
        dict: Données structurées de l'AG (résolutions, votes, quorum, etc.)

    Raises:
        ValueError: Si Claude ne retourne pas un JSON valide
        anthropic.APIError: En cas d'erreur API
    """
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_ANALYSE_AG,
        messages=[
            {
                "role": "user",
                "content": f"Analyse cette transcription d'assemblée générale et retourne le JSON structuré :\n\n{transcription}",
            }
        ],
    )

    contenu = message.content[0].text.strip()

    # Nettoyer les balises markdown si présentes
    if contenu.startswith("```"):
        lignes = contenu.split("\n")
        contenu = "\n".join(lignes[1:-1] if lignes[-1] == "```" else lignes[1:])

    try:
        return json.loads(contenu)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude n'a pas retourné un JSON valide : {e}\n\nRéponse brute :\n{contenu}")


def poser_question(transcription: str, analyse: dict, question: str, api_key: str) -> str:
    """
    Répond à une question sur l'AG en se basant sur la transcription et l'analyse.

    Args:
        transcription: Texte brut de la transcription
        analyse: JSON structuré produit par analyser_transcription()
        question: Question de l'utilisateur
        api_key: Clé API Anthropic

    Returns:
        str: Réponse en langage naturel
    """
    client = anthropic.Anthropic(api_key=api_key)

    contexte = f"""Transcription de l'AG :
{transcription}

Analyse structurée :
{json.dumps(analyse, ensure_ascii=False, indent=2)}

Question : {question}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_QA_AG,
        messages=[{"role": "user", "content": contexte}],
    )

    return message.content[0].text.strip()
