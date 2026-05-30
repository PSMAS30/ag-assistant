"""
test_historique_manager.py — Tests historique_manager.py (sans API)
Couvre : sauvegarde, lecture, suppression, audit trail,
         dossiers par entite, comparaison N/N-1, export/import ZIP.
"""

import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _fixture(nom):
    with open(FIXTURES_DIR / nom, encoding="utf-8") as f:
        return json.load(f)


# ── Tests de base ─────────────────────────────────────────────────────────────

def test_sauvegarder_et_lister(tmp_path, monkeypatch):
    """Sauvegarde une AG et verifie qu elle apparait dans la liste."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    chemin = historique_manager.sauvegarder_ag(f, pv_texte="PV de test")
    assert Path(chemin).exists()
    ag_list = historique_manager.lister_ag()
    assert len(ag_list) == 1
    assert "Acacias" in ag_list[0]["entite"]


def test_charger_ag(tmp_path, monkeypatch):
    """Charge une AG sauvegardee et verifie le contenu."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_association.json")
    chemin = historique_manager.sauvegarder_ag(f, pv_texte="PV asso")
    entree = historique_manager.charger_ag(chemin)
    assert entree["pv_texte"] == "PV asso"
    assert entree["analyse"]["type_ag"] == "association"


def test_supprimer_ag(tmp_path, monkeypatch):
    """Supprime une AG et verifie qu elle disparait de la liste."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_pme.json")
    chemin = historique_manager.sauvegarder_ag(f)
    assert historique_manager.nb_ag_sauvegardees() == 1
    historique_manager.supprimer_ag(chemin)
    assert historique_manager.nb_ag_sauvegardees() == 0


def test_audit_trail(tmp_path, monkeypatch):
    """L audit trail enregistre les actions successives."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    chemin = historique_manager.sauvegarder_ag(f)
    historique_manager.ajouter_action_audit(chemin, "pdf_exporte", "proces_verbal.pdf")
    historique_manager.ajouter_action_audit(chemin, "word_exporte", "proces_verbal.docx")
    entree = historique_manager.charger_ag(chemin)
    actions = [a["action"] for a in entree["meta_historique"]["audit_trail"]]
    assert "analyse_sauvegardee" in actions
    assert "pdf_exporte" in actions
    assert "word_exporte" in actions
    assert len(actions) == 3


def test_nb_ag_sauvegardees(tmp_path, monkeypatch):
    """nb_ag_sauvegardees retourne le bon compte total."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    assert historique_manager.nb_ag_sauvegardees() == 0
    for nom in ["analyse_copropriete.json", "analyse_association.json", "analyse_pme.json"]:
        historique_manager.sauvegarder_ag(_fixture(nom))
    assert historique_manager.nb_ag_sauvegardees() == 3


def test_historique_vide(tmp_path, monkeypatch):
    """lister_ag retourne liste vide si aucune AG."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    assert historique_manager.lister_ag() == []


# ── Tests dossiers par entite ─────────────────────────────────────────────────

def test_sauvegarde_cree_sous_dossier(tmp_path, monkeypatch):
    """Chaque AG est sauvegardee dans un sous-dossier nomme d apres l entite."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    chemin = historique_manager.sauvegarder_ag(f)
    p = Path(chemin)
    # Le fichier doit etre dans un sous-dossier (pas directement dans tmp_path)
    assert p.parent != tmp_path
    assert p.parent.is_dir()


def test_entites_differentes_dans_dossiers_separes(tmp_path, monkeypatch):
    """Deux entites differentes → deux sous-dossiers distincts."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    dossiers = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(dossiers) == 2


def test_meme_entite_meme_dossier(tmp_path, monkeypatch):
    """Deux AG de la meme entite → meme sous-dossier."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    c1 = historique_manager.sauvegarder_ag(f)
    c2 = historique_manager.sauvegarder_ag(f)
    assert Path(c1).parent == Path(c2).parent
    assert len(list(Path(c1).parent.glob("*.json"))) == 2


def test_lister_dossiers(tmp_path, monkeypatch):
    """lister_dossiers retourne la liste des entites avec leur nb d AG."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    dossiers = historique_manager.lister_dossiers()
    assert len(dossiers) == 2
    assert all("dossier" in d and "nb_ag" in d and "entite" in d for d in dossiers)
    assert all(d["nb_ag"] == 1 for d in dossiers)


def test_lister_ag_par_dossier(tmp_path, monkeypatch):
    """lister_ag(dossier=X) ne retourne que les AG de ce dossier."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    dossiers = historique_manager.lister_dossiers()
    nom_dossier_copro = dossiers[0]["dossier"]
    ag_filtrees = historique_manager.lister_ag(dossier=nom_dossier_copro)
    assert len(ag_filtrees) == 1


def test_nb_ag_par_dossier(tmp_path, monkeypatch):
    """nb_ag_sauvegardees(dossier=X) compte uniquement ce dossier."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    historique_manager.sauvegarder_ag(f)
    historique_manager.sauvegarder_ag(f)
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    dossiers = historique_manager.lister_dossiers()
    dossier_copro = next(d for d in dossiers if "Acacias" in d["entite"])
    assert historique_manager.nb_ag_sauvegardees(dossier=dossier_copro["dossier"]) == 2
    assert historique_manager.nb_ag_sauvegardees() == 3


def test_lister_ag_contient_champ_dossier(tmp_path, monkeypatch):
    """Chaque entree retournee par lister_ag contient le champ 'dossier'."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    ag_list = historique_manager.lister_ag()
    assert "dossier" in ag_list[0]
    assert ag_list[0]["dossier"] != ""


def test_supprimer_ag_nettoie_dossier_vide(tmp_path, monkeypatch):
    """Supprimer la derniere AG d un dossier supprime aussi le dossier."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_association.json")
    chemin = historique_manager.sauvegarder_ag(f)
    dossier = Path(chemin).parent
    assert dossier.exists()
    historique_manager.supprimer_ag(chemin)
    assert not dossier.exists()


def test_supprimer_ag_conserve_dossier_si_autres_ag(tmp_path, monkeypatch):
    """Supprimer une AG ne supprime pas le dossier si d autres AG y restent."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    c1 = historique_manager.sauvegarder_ag(f)
    c2 = historique_manager.sauvegarder_ag(f)
    dossier = Path(c1).parent
    historique_manager.supprimer_ag(c1)
    assert dossier.exists()  # dossier conserve car c2 existe encore
    assert Path(c2).exists()


def test_migration_fichiers_plats(tmp_path, monkeypatch):
    """Les fichiers JSON plats (ancienne version) sont migres vers des sous-dossiers."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    # Simuler un ancien fichier plat
    f = _fixture("analyse_copropriete.json")
    ancien_fichier = tmp_path / "20240615_120000_test.json"
    entree = {
        "meta_historique": {"entite": "Copropriete Les Acacias", "type_ag": "copropriete", "sauvegarde_le": "2024-06-15T12:00:00", "date_ag": "15/06/2024", "nb_resolutions": 4, "a_pv": False, "audit_trail": []},
        "analyse": f,
        "pv_texte": None,
    }
    with open(ancien_fichier, "w", encoding="utf-8") as fp:
        json.dump(entree, fp)
    # lister_ag doit declencher la migration
    ag_list = historique_manager.lister_ag()
    assert len(ag_list) == 1
    # Le fichier plat ne doit plus exister
    assert not ancien_fichier.exists()
    # Il doit etre dans un sous-dossier
    assert Path(ag_list[0]["fichier"]).parent != tmp_path


# ── Tests export / import ZIP ─────────────────────────────────────────────────

def test_export_import_historique_complet(tmp_path, monkeypatch):
    """Export tout l historique → import dans un nouveau dossier."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    zip_bytes = historique_manager.exporter_historique()
    assert len(zip_bytes) > 0
    # Importer dans un nouveau dossier
    tmp2 = tmp_path / "import"
    tmp2.mkdir()
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp2)
    nb = historique_manager.importer_historique(zip_bytes)
    assert nb == 2
    assert historique_manager.nb_ag_sauvegardees() == 2


def test_export_dossier_specifique(tmp_path, monkeypatch):
    """Export d un seul dossier ne contient que ses AG."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    historique_manager.sauvegarder_ag(_fixture("analyse_copropriete.json"))
    historique_manager.sauvegarder_ag(_fixture("analyse_association.json"))
    dossiers = historique_manager.lister_dossiers()
    nom_copro = dossiers[0]["dossier"]
    zip_bytes = historique_manager.exporter_historique(dossier=nom_copro)
    # Importer → seulement 1 AG
    tmp2 = tmp_path / "import2"
    tmp2.mkdir()
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp2)
    nb = historique_manager.importer_historique(zip_bytes)
    assert nb == 1


def test_export_historique_vide(tmp_path, monkeypatch):
    """Export d un historique vide retourne des bytes (ZIP vide valide)."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    zip_bytes = historique_manager.exporter_historique()
    assert isinstance(zip_bytes, bytes)


def test_import_zip_plat_retrocompatibilite(tmp_path, monkeypatch):
    """Import d un ZIP sans sous-dossiers (ancienne version) fonctionne."""
    import historique_manager, zipfile, io
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    entree = {
        "meta_historique": {"entite": "Copropriete Les Acacias", "type_ag": "copropriete", "sauvegarde_le": "2024-06-15T12:00:00", "date_ag": "15/06/2024", "nb_resolutions": 4, "a_pv": False, "audit_trail": []},
        "analyse": f, "pv_texte": None,
    }
    # Creer ZIP plat (sans sous-dossier)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("20240615_copropriete.json", json.dumps(entree))
    nb = historique_manager.importer_historique(buf.getvalue())
    assert nb == 1
    assert historique_manager.nb_ag_sauvegardees() == 1


# ── Tests comparaison N vs N-1 ────────────────────────────────────────────────

def test_comparer_ag_structure(tmp_path, monkeypatch):
    """comparer_ag retourne un rapport avec les cles attendues."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    c1 = historique_manager.sauvegarder_ag(f)
    c2 = historique_manager.sauvegarder_ag(f)
    rapport = historique_manager.comparer_ag(c1, c2)
    assert "ag1" in rapport
    assert "ag2" in rapport
    assert "quorum" in rapport
    assert "participants" in rapport
    assert "resolutions_communes" in rapport
    assert "nouvelles_resolutions" in rapport
    assert "resolutions_disparues" in rapport


def test_comparer_ag_resolutions_communes(tmp_path, monkeypatch):
    """Deux AG identiques ont toutes leurs resolutions en commun."""
    import historique_manager
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    f = _fixture("analyse_copropriete.json")
    c1 = historique_manager.sauvegarder_ag(f)
    c2 = historique_manager.sauvegarder_ag(f)
    rapport = historique_manager.comparer_ag(c1, c2)
    nb_res = len(f.get("resolutions", []))
    assert len(rapport["resolutions_communes"]) == nb_res
    assert len(rapport["nouvelles_resolutions"]) == 0
    assert len(rapport["resolutions_disparues"]) == 0


def test_comparer_ag_detection_changement_statut(tmp_path, monkeypatch):
    """comparer_ag detecte un changement de statut sur une resolution."""
    import historique_manager, copy
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    import time
    f1 = _fixture("analyse_copropriete.json")
    f2 = copy.deepcopy(f1)
    # Changer le statut de la resolution 1
    if f2.get("resolutions"):
        f2["resolutions"][0]["statut"] = "rejetée"
    c1 = historique_manager.sauvegarder_ag(f1)
    time.sleep(0.01)
    c2 = historique_manager.sauvegarder_ag(f2)
    rapport = historique_manager.comparer_ag(c1, c2)
    changed = [r for r in rapport["resolutions_communes"] if r["statut_change"]]
    assert len(changed) >= 1
