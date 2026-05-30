"""
pv_generator.py — Genere un proces-verbal formate (texte + PDF) a partir de l analyse AG
"""

import json
from datetime import datetime
import anthropic
from prompts import SYSTEM_PV_GENERATOR
from prompts_v2 import get_template_pv


def generer_pv_texte(analyse: dict, api_key: str) -> str:
    """
    Genere le texte du PV a partir de l analyse structuree via Claude.

    Args:
        analyse: JSON structure produit par analyzer.analyser_transcription()
        api_key: Cle API Anthropic

    Returns:
        str: Texte complet du PV, pret a etre exporte
    """
    client = anthropic.Anthropic(api_key=api_key)

    # BUG FIX : lire type_ag au niveau racine du dict (format v2)
    type_ag = analyse.get("type_ag", "autre")
    system_prompt = get_template_pv(type_ag)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Redige le proces-verbal complet de cette assemblee generale :\n\n{json.dumps(analyse, ensure_ascii=False, indent=2)}",
            }
        ],
    )

    return message.content[0].text.strip()


_EMOJI_MAP = {
    "✅": "[OK]", "❌": "[NON]", "⚠️": "[ATTENTION]", "🏛️": "",
    "🎙️": "", "📋": "", "📄": "", "💬": "", "🔑": "", "🎭": "",
    "📁": "", "📥": "", "⬇️": "", "🔍": "", "⚖️": "", "🗣️": "",
    "✏️": "", "📜": "", "📍": "", "👤": "", "✍️": "", "💡": "",
    "🔴": "[!]", "ℹ️": "[i]",
}

def _sanitiser_latin1(texte: str) -> str:
    """Remplace les emoji et caracteres hors latin-1 pour compatibilite Helvetica."""
    for emoji, remplacement in _EMOJI_MAP.items():
        texte = texte.replace(emoji, remplacement)
    # Supprime les caracteres restants hors latin-1
    return texte.encode("latin-1", errors="ignore").decode("latin-1")


def exporter_pv_pdf(texte_pv: str, chemin_sortie: str, titre: str = "Proces-Verbal d Assemblee Generale") -> str:
    """
    Exporte le PV en PDF via fpdf2.

    Args:
        texte_pv: Texte du PV genere par generer_pv_texte()
        chemin_sortie: Chemin du fichier PDF a creer
        titre: Titre affiche en en-tete du PDF

    Returns:
        str: Chemin du fichier PDF cree
    """
    from fpdf import FPDF

    # Sanitiser le texte (emoji + caracteres hors latin-1 incompatibles avec Helvetica)
    texte_propre = _sanitiser_latin1(texte_pv)

    pdf = FPDF()
    pdf.set_margins(left=20, top=20, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    largeur = pdf.w - pdf.l_margin - pdf.r_margin  # largeur utile

    # En-tete
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(largeur, 10, _sanitiser_latin1(titre), align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(largeur, 6, f"Document genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}", align="C")
    pdf.ln(6)

    # Corps du PV
    pdf.set_font("Helvetica", "", 11)
    for ligne in texte_propre.split("\n"):
        ligne = ligne.strip()
        if not ligne:
            pdf.ln(4)
            continue
        # Titres de section en gras
        if ligne.startswith("---") or ligne.isupper() or (ligne.startswith("RESOLUTION") and ":" in ligne):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(largeur, 6, ligne)
            pdf.set_font("Helvetica", "", 11)
        else:
            pdf.multi_cell(largeur, 6, ligne)

    # Pied de page
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Document genere par AG Assistant | github.com/PSMAS30/ag-assistant", align="C")

    pdf.output(chemin_sortie)
    return chemin_sortie


def pv_demo(analyse: dict) -> str:
    """
    Genere un PV sans appel API (mode demo) — utilise un template statique.
    Compatible avec le format JSON v2 (informations_generales, resolutions.statut, etc.)
    """
    # Lecture format v2
    infos = analyse.get("informations_generales", {})
    entite = infos.get("entite", analyse.get("entite", "Entite inconnue"))
    date = infos.get("date", analyse.get("date", "date inconnue"))
    lieu = infos.get("lieu", analyse.get("lieu", "lieu non precise"))
    president = infos.get("president_seance", analyse.get("presidence", "President(e) non precise(e)"))
    secretaire = infos.get("secretaire", "non mentionne")
    heure_ouverture = infos.get("heure_ouverture", "")
    heure_cloture = infos.get("heure_cloture", "")

    participants = analyse.get("participants", {})
    total_presents = participants.get("total_presents", participants.get("presents", "N/A"))
    # Si presents est une liste (format v2), compter
    if isinstance(total_presents, list):
        total_presents = len(total_presents)
    total_representes = participants.get("total_representes", participants.get("representes", "N/A"))
    if isinstance(total_representes, list):
        total_representes = len(total_representes)
    total_votants = participants.get("total_votants", "N/A")
    quorum_atteint = participants.get("quorum_atteint")
    quorum_requis = participants.get("quorum_requis", "")

    resolutions = analyse.get("resolutions", [])
    points_divers = analyse.get("points_divers", analyse.get("incidents_divers", []))

    lignes = [
        "PROCES-VERBAL D ASSEMBLEE GENERALE",
        "=" * 50,
        entite,
        "",
        f"Date       : {date}",
        f"Lieu       : {lieu}",
        f"Ouverture  : {heure_ouverture or 'non mentionne'}",
        f"President  : {president}",
        f"Secretaire : {secretaire}",
        "",
        "--- QUORUM ---",
        f"Presents    : {total_presents}",
        f"Representes : {total_representes}",
        f"Total votants: {total_votants}",
    ]
    if quorum_requis:
        lignes.append(f"Quorum requis: {quorum_requis}")
    lignes.append(f"Quorum atteint: {'OUI' if quorum_atteint is True else 'NON' if quorum_atteint is False else 'N/A'}")

    if resolutions:
        lignes += ["", "--- RESOLUTIONS ---"]
        for r in resolutions:
            votes = r.get("votes", {})
            # Format v2 : statut = "adoptee" | "rejetee" ; format v1 : resultat = "adopte" | "rejete"
            statut = r.get("statut", r.get("resultat", ""))
            if statut in ("adoptée", "adopte"):
                label = "ADOPTEE"
            elif statut in ("rejetée", "rejete"):
                label = "REJETEE"
            else:
                label = statut.upper() if statut else "?"
            titre_r = r.get("titre", r.get("intitule", ""))
            abstentions = votes.get("abstentions", votes.get("abstention", "?"))
            lignes += [
                "",
                f"RESOLUTION N{r.get('numero', '?')} : {titre_r}",
                f"{r.get('description', '')}",
                f"Vote — Pour : {votes.get('pour', '?')} | Contre : {votes.get('contre', '?')} | Abstentions : {abstentions} {votes.get('unite', '')}",
                f"→ {label}",
            ]
            if r.get("base_legale") and r["base_legale"] != "non mentionne dans la transcription":
                lignes.append(f"   Base legale : {r['base_legale']}")

    if points_divers:
        lignes += ["", "--- QUESTIONS DIVERSES ---"]
        for pt in points_divers:
            lignes.append(f"• {pt}")

    if heure_cloture and heure_cloture != "non mentionne dans la transcription":
        lignes += ["", f"Seance levee a {heure_cloture}."]

    lignes += [
        "",
        "Le President de seance",
        "___________________________",
        "",
        "Le Secretaire de seance",
        "___________________________",
        "",
        "[Document genere en mode demo — AG Assistant]",
        "[Ce document est provisoire et doit etre relu, corrige et signe avant toute valeur juridique.]",
    ]

    return "\n".join(lignes)
