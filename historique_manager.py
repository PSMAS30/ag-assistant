"""
historique_manager.py — Gestion de l historique des AG analysees
Stockage local dans historique/ — un fichier JSON par AG.
Inclut audit trail basique (actions horodatees).
"""

import json
import os
from datetime import datetime
from pathlib import Path

HISTORIQUE_DIR = Path(__file__).parent / "historique"


def _assurer_dossier():
    """Cree le dossier historique s il n existe pas."""
    HISTORIQUE_DIR.mkdir(exist_ok=True)


def _nom_fichier(entite: str, type_ag: str) -> str:
    """Genere un nom de fichier unique base sur timestamp + entite."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    entite_clean = "".join(c for c in entite if c.isalnum() or c in " _-")[:30].strip().replace(" ", "_")
    return f"{ts}_{entite_clean}.json"


def sauvegarder_ag(analyse: dict, pv_texte: str = None) -> str:
    """
    Sauvegarde une AG analysee dans l historique.

    Args:
        analyse: JSON structure produit par analyzer.analyser_transcription()
        pv_texte: Texte du PV genere (optionnel)

    Returns:
        str: Chemin du fichier sauvegarde
    """
    _assurer_dossier()

    infos = analyse.get("informations_generales", {})
    entite = infos.get("entite", analyse.get("entite", "Entite_inconnue"))
    type_ag = analyse.get("type_ag", "autre")
    date_ag = infos.get("date", analyse.get("date", ""))
    nb_resolutions = len(analyse.get("resolutions", []))

    entree = {
        "meta_historique": {
            "sauvegarde_le": datetime.now().isoformat(),
            "entite": entite,
            "type_ag": type_ag,
            "date_ag": date_ag,
            "nb_resolutions": nb_resolutions,
            "a_pv": pv_texte is not None,
            "audit_trail": [
                {
                    "action": "analyse_sauvegardee",
                    "timestamp": datetime.now().isoformat(),
                    "details": f"AG de {entite} — {nb_resolutions} resolution(s)",
                }
            ],
        },
        "analyse": analyse,
        "pv_texte": pv_texte,
    }

    nom = _nom_fichier(entite, type_ag)
    chemin = HISTORIQUE_DIR / nom
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(entree, f, ensure_ascii=False, indent=2)

    return str(chemin)


def ajouter_action_audit(chemin_fichier: str, action: str, details: str = "") -> None:
    """
    Ajoute une action a l audit trail d une AG sauvegardee.

    Args:
        chemin_fichier: Chemin du fichier JSON de l AG
        action: Type d action (ex: 'pv_genere', 'pdf_exporte', 'word_exporte')
        details: Description optionnelle
    """
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            entree = json.load(f)
        entree["meta_historique"]["audit_trail"].append({
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })
        if action in ("pv_genere",) and details:
            entree["pv_texte"] = details
            entree["meta_historique"]["a_pv"] = True
        with open(chemin_fichier, "w", encoding="utf-8") as f:
            json.dump(entree, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # Audit trail non bloquant


def lister_ag() -> list:
    """
    Retourne la liste des AG sauvegardees, triees par date decroissante.

    Returns:
        list: [{fichier, entite, type_ag, date_ag, nb_resolutions, a_pv, sauvegarde_le}]
    """
    _assurer_dossier()
    ag_list = []
    for fichier in sorted(HISTORIQUE_DIR.glob("*.json"), reverse=True):
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                entree = json.load(f)
            meta = entree.get("meta_historique", {})
            ag_list.append({
                "fichier": str(fichier),
                "nom_fichier": fichier.name,
                "entite": meta.get("entite", "Inconnu"),
                "type_ag": meta.get("type_ag", "autre"),
                "date_ag": meta.get("date_ag", ""),
                "nb_resolutions": meta.get("nb_resolutions", 0),
                "a_pv": meta.get("a_pv", False),
                "sauvegarde_le": meta.get("sauvegarde_le", ""),
                "audit_trail": meta.get("audit_trail", []),
            })
        except Exception:
            continue
    return ag_list


def charger_ag(chemin_fichier: str) -> dict:
    """
    Charge une AG depuis l historique.

    Returns:
        dict: {"analyse": dict, "pv_texte": str|None, "meta_historique": dict}
    """
    with open(chemin_fichier, "r", encoding="utf-8") as f:
        return json.load(f)


def supprimer_ag(chemin_fichier: str) -> bool:
    """Supprime une AG de l historique."""
    try:
        os.unlink(chemin_fichier)
        return True
    except Exception:
        return False


def nb_ag_sauvegardees() -> int:
    """Retourne le nombre d AG dans l historique."""
    _assurer_dossier()
    return len(list(HISTORIQUE_DIR.glob("*.json")))
