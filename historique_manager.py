"""
historique_manager.py — Gestion de l historique des AG analysees
Stockage par dossier entite : historique/{entite}/{timestamp}.json
Inclut audit trail, comparaison N vs N-1, export/import ZIP.
"""

import json
import os
from datetime import datetime
from pathlib import Path

HISTORIQUE_DIR = Path(__file__).parent / "historique"


def _assurer_dossier():
    """Cree le dossier historique s il n existe pas."""
    HISTORIQUE_DIR.mkdir(exist_ok=True)


def _nom_dossier(entite: str) -> str:
    """Sanitize le nom d entite pour en faire un nom de dossier valide."""
    clean = "".join(c for c in entite if c.isalnum() or c in " _-")[:40].strip()
    return clean.replace(" ", "_") or "Sans_nom"


def _nom_fichier(type_ag: str) -> str:
    """Genere un nom de fichier unique base sur le timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{type_ag}.json"


def _migrer_fichiers_plats() -> int:
    """
    Migration transparente : deplace les anciens fichiers JSON plats
    (historique/*.json) dans leurs sous-dossiers respectifs.

    Returns:
        int: Nombre de fichiers migres
    """
    _assurer_dossier()
    count = 0
    for fichier in list(HISTORIQUE_DIR.glob("*.json")):
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                entree = json.load(f)
            meta = entree.get("meta_historique", {})
            entite = meta.get("entite", "Sans_nom")
            nom_dossier = _nom_dossier(entite)
            sous_dossier = HISTORIQUE_DIR / nom_dossier
            sous_dossier.mkdir(exist_ok=True)
            dest = sous_dossier / fichier.name
            fichier.rename(dest)
            # Mettre a jour le champ dossier dans la meta
            entree["meta_historique"]["dossier"] = nom_dossier
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(entree, f, ensure_ascii=False, indent=2)
            count += 1
        except Exception:
            continue
    return count


def sauvegarder_ag(analyse: dict, pv_texte: str = None) -> str:
    """
    Sauvegarde une AG analysee dans l historique.
    Chemin : historique/{entite}/{timestamp}_{type_ag}.json

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
    nom_dossier = _nom_dossier(entite)

    # Creer le sous-dossier entite
    sous_dossier = HISTORIQUE_DIR / nom_dossier
    sous_dossier.mkdir(exist_ok=True)

    entree = {
        "meta_historique": {
            "sauvegarde_le": datetime.now().isoformat(),
            "entite": entite,
            "dossier": nom_dossier,
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

    nom = _nom_fichier(type_ag)
    chemin = sous_dossier / nom
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


def lister_dossiers() -> list:
    """
    Retourne la liste des dossiers (entites) dans l historique.

    Returns:
        list: [{"dossier": str, "nb_ag": int, "entite": str}]
    """
    _assurer_dossier()
    _migrer_fichiers_plats()
    dossiers = []
    for d in sorted(HISTORIQUE_DIR.iterdir()):
        if d.is_dir():
            nb = len(list(d.glob("*.json")))
            if nb > 0:
                dossiers.append({
                    "dossier": d.name,
                    "entite": d.name.replace("_", " "),
                    "nb_ag": nb,
                })
    return dossiers


def lister_ag(dossier: str = None) -> list:
    """
    Retourne la liste des AG sauvegardees, triees par date decroissante.

    Args:
        dossier: Nom du sous-dossier (entite) — None = toutes les entites

    Returns:
        list: [{fichier, nom_fichier, dossier, entite, type_ag, date_ag,
                nb_resolutions, a_pv, sauvegarde_le, audit_trail}]
    """
    _assurer_dossier()
    _migrer_fichiers_plats()

    if dossier:
        pattern = f"{dossier}/*.json"
    else:
        pattern = "**/*.json"

    ag_list = []
    for fichier in sorted(HISTORIQUE_DIR.glob(pattern), reverse=True):
        if not fichier.is_file():
            continue
        try:
            with open(fichier, "r", encoding="utf-8") as f:
                entree = json.load(f)
            meta = entree.get("meta_historique", {})
            ag_list.append({
                "fichier": str(fichier),
                "nom_fichier": fichier.name,
                "dossier": fichier.parent.name,
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
    """Supprime une AG et nettoie le dossier si vide."""
    try:
        chemin = Path(chemin_fichier)
        os.unlink(chemin_fichier)
        # Nettoyer le dossier parent s il est vide
        parent = chemin.parent
        if parent != HISTORIQUE_DIR and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
        return True
    except Exception:
        return False


def nb_ag_sauvegardees(dossier: str = None) -> int:
    """Retourne le nombre d AG dans l historique (total ou par dossier)."""
    _assurer_dossier()
    if dossier:
        return len(list((HISTORIQUE_DIR / dossier).glob("*.json")))
    return len(list(HISTORIQUE_DIR.glob("**/*.json")))


# ── Export / Import historique ────────────────────────────────────────────────

def exporter_historique(dossier: str = None) -> bytes:
    """
    Exporte l historique en ZIP en preservant l arborescence par entite.

    Args:
        dossier: Exporter un seul dossier (None = tout)

    Returns:
        bytes: Archive ZIP avec structure {dossier}/{fichier}.json
    """
    import zipfile, io
    _assurer_dossier()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if dossier:
            sous_dir = HISTORIQUE_DIR / dossier
            for fichier in sous_dir.glob("*.json"):
                zf.write(fichier, f"{dossier}/{fichier.name}")
        else:
            for fichier in HISTORIQUE_DIR.glob("**/*.json"):
                # Chemin relatif : {dossier}/{fichier.json}
                rel = fichier.relative_to(HISTORIQUE_DIR)
                zf.write(fichier, str(rel))
    return buffer.getvalue()


def importer_historique(zip_bytes: bytes) -> int:
    """
    Importe un historique depuis un ZIP.
    Supporte ZIP plat (ancienne version) et ZIP avec sous-dossiers.

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
            if not name.endswith(".json"):
                continue
            parts = name.replace("\\", "/").split("/")
            if len(parts) == 1:
                # Fichier plat (ancienne version) — detecter le dossier depuis le contenu
                try:
                    data = json.loads(zf.read(name))
                    meta = data.get("meta_historique", {})
                    entite = meta.get("entite", "Import")
                    nom_dossier = _nom_dossier(entite)
                except Exception:
                    nom_dossier = "Import"
                dest_dir = HISTORIQUE_DIR / nom_dossier
            else:
                # Fichier avec sous-dossier : {dossier}/{fichier}.json
                nom_dossier = parts[0]
                dest_dir = HISTORIQUE_DIR / nom_dossier

            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / parts[-1]
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
        dict: Rapport de comparaison
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
        "ag1": {"entite": meta1.get("entite"), "date": meta1.get("date_ag"), "dossier": meta1.get("dossier", ""), "sauvegarde_le": meta1.get("sauvegarde_le", "")[:10]},
        "ag2": {"entite": meta2.get("entite"), "date": meta2.get("date_ag"), "dossier": meta2.get("dossier", ""), "sauvegarde_le": meta2.get("sauvegarde_le", "")[:10]},
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
