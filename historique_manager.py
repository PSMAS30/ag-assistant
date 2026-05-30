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


# ── Export / Import historique ────────────────────────────────────────────────

def exporter_historique() -> bytes:
    """
    Exporte tout l historique en ZIP (bytes).
    Permet de sauvegarder et restaurer l historique sur Streamlit Cloud.

    Returns:
        bytes: Archive ZIP contenant tous les fichiers JSON de l historique
    """
    import zipfile, io
    _assurer_dossier()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fichier in HISTORIQUE_DIR.glob("*.json"):
            zf.write(fichier, fichier.name)
    return buffer.getvalue()


def importer_historique(zip_bytes: bytes) -> int:
    """
    Importe un historique depuis un ZIP.

    Args:
        zip_bytes: Contenu du fichier ZIP

    Returns:
        int: Nombre de fichiers importes
    """
    import zipfile, io
    _assurer_dossier()
    count = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if name.endswith(".json") and "/" not in name:
                dest = HISTORIQUE_DIR / name
                dest.write_bytes(zf.read(name))
                count += 1
    return count


# ── Comparaison N vs N-1 ──────────────────────────────────────────────────────

def comparer_ag(chemin_ag1: str, chemin_ag2: str) -> dict:
    """
    Compare deux AG et retourne un rapport de differences.

    Args:
        chemin_ag1: Fichier AG N-1 (plus ancienne)
        chemin_ag2: Fichier AG N (plus recente)

    Returns:
        dict: Rapport de comparaison {
            "ag1": meta AG1,
            "ag2": meta AG2,
            "quorum": {ag1, ag2, evolution},
            "participants": {ag1, ag2, evolution},
            "resolutions": [comparaison par titre],
            "nouvelles_resolutions": [],
            "resolutions_disparues": [],
        }
    """
    entree1 = charger_ag(chemin_ag1)
    entree2 = charger_ag(chemin_ag2)
    a1 = entree1.get("analyse", {})
    a2 = entree2.get("analyse", {})
    meta1 = entree1.get("meta_historique", {})
    meta2 = entree2.get("meta_historique", {})

    p1 = a1.get("participants", {})
    p2 = a2.get("participants", {})

    def _voix(p):
        v = p.get("total_voix") or p.get("total_votants")
        return int(v) if v and str(v).isdigit() else None

    def _quorum_calcule(p):
        q = p.get("quorum_calcule")
        return int(q) if q and str(q).isdigit() else None

    # Comparaison resolutions par titre normalise
    def _normaliser(titre: str) -> str:
        return titre.lower().strip() if titre else ""

    res1 = {_normaliser(r.get("titre", r.get("intitule", ""))): r for r in a1.get("resolutions", [])}
    res2 = {_normaliser(r.get("titre", r.get("intitule", ""))): r for r in a2.get("resolutions", [])}

    titres_communs = set(res1.keys()) & set(res2.keys())
    titres_nouveaux = set(res2.keys()) - set(res1.keys())
    titres_disparus = set(res1.keys()) - set(res2.keys())

    comparaison_resolutions = []
    for titre in titres_communs:
        r1 = res1[titre]
        r2 = res2[titre]
        v1 = r1.get("votes", {})
        v2 = r2.get("votes", {})
        statut1 = r1.get("statut", r1.get("resultat", ""))
        statut2 = r2.get("statut", r2.get("resultat", ""))
        comparaison_resolutions.append({
            "titre": r2.get("titre", r2.get("intitule", titre)),
            "statut_ag1": statut1,
            "statut_ag2": statut2,
            "statut_change": statut1 != statut2,
            "votes_ag1": {"pour": v1.get("pour"), "contre": v1.get("contre"), "abstentions": v1.get("abstentions", v1.get("abstention"))},
            "votes_ag2": {"pour": v2.get("pour"), "contre": v2.get("contre"), "abstentions": v2.get("abstentions", v2.get("abstention"))},
        })

    return {
        "ag1": {"entite": meta1.get("entite"), "date": meta1.get("date_ag"), "sauvegarde_le": meta1.get("sauvegarde_le", "")[:10]},
        "ag2": {"entite": meta2.get("entite"), "date": meta2.get("date_ag"), "sauvegarde_le": meta2.get("sauvegarde_le", "")[:10]},
        "quorum": {
            "ag1_atteint": p1.get("quorum_atteint"),
            "ag2_atteint": p2.get("quorum_atteint"),
            "ag1_calcule": _quorum_calcule(p1),
            "ag2_calcule": _quorum_calcule(p2),
        },
        "participants": {
            "ag1_votants": p1.get("total_votants"),
            "ag2_votants": p2.get("total_votants"),
            "ag1_voix": _voix(p1),
            "ag2_voix": _voix(p2),
        },
        "resolutions_communes": sorted(comparaison_resolutions, key=lambda x: x["titre"]),
        "nouvelles_resolutions": [res2[t].get("titre", t) for t in titres_nouveaux],
        "resolutions_disparues": [res1[t].get("titre", t) for t in titres_disparus],
        "nb_resolutions_ag1": len(res1),
        "nb_resolutions_ag2": len(res2),
    }
