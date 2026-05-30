"""
test_historique_demo.py — Tests des donnees demo historique et dossiers illustres
Verifie : 2 AG pour Les Acacias, dossiers separes, comparaison N/N-1 significative.
"""

import pytest
from pathlib import Path


def test_demo_historique_contient_4_ag():
    """Le module demo contient bien 4 AG."""
    import historique_demo
    assert len(historique_demo.DEMO_HISTORIQUE) == 4


def test_demo_historique_2_acacias():
    """Il y a exactement 2 AG pour Copropriete Les Acacias (2023 + 2024)."""
    import historique_demo
    acacias = [e for e in historique_demo.DEMO_HISTORIQUE
               if "Acacias" in e["analyse"]["informations_generales"]["entite"]]
    assert len(acacias) == 2
    dates = {e["analyse"]["informations_generales"]["date"] for e in acacias}
    assert "17/06/2023" in dates
    assert "15/06/2024" in dates


def test_demo_historique_entites_distinctes():
    """Les 4 AG ont au moins 3 entites distinctes."""
    import historique_demo
    entites = {e["analyse"]["informations_generales"]["entite"] for e in historique_demo.DEMO_HISTORIQUE}
    assert len(entites) >= 3


def test_charger_demo_dans_historique(tmp_path, monkeypatch):
    """Charger les AG demo cree les bons dossiers dans l historique."""
    import historique_manager, historique_demo
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    for entree in historique_demo.DEMO_HISTORIQUE:
        historique_manager.sauvegarder_ag(entree["analyse"])
    assert historique_manager.nb_ag_sauvegardees() == 4
    dossiers = historique_manager.lister_dossiers()
    assert len(dossiers) >= 3  # Acacias + Elan Vitry + Innov Tech


def test_dossier_acacias_contient_2_ag(tmp_path, monkeypatch):
    """Apres chargement demo, le dossier Les Acacias contient 2 AG."""
    import historique_manager, historique_demo
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    for entree in historique_demo.DEMO_HISTORIQUE:
        historique_manager.sauvegarder_ag(entree["analyse"])
    dossiers = historique_manager.lister_dossiers()
    dossier_acacias = next((d for d in dossiers if "Acacias" in d["entite"]), None)
    assert dossier_acacias is not None
    assert dossier_acacias["nb_ag"] == 2


def test_filtrer_ag_par_dossier_acacias(tmp_path, monkeypatch):
    """lister_ag(dossier=Acacias) retourne uniquement les 2 AG Acacias."""
    import historique_manager, historique_demo
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    for entree in historique_demo.DEMO_HISTORIQUE:
        historique_manager.sauvegarder_ag(entree["analyse"])
    dossiers = historique_manager.lister_dossiers()
    dossier_acacias = next(d for d in dossiers if "Acacias" in d["entite"])
    ag_acacias = historique_manager.lister_ag(dossier=dossier_acacias["dossier"])
    assert len(ag_acacias) == 2
    for ag in ag_acacias:
        assert "Acacias" in ag["entite"]


def test_comparaison_acacias_2023_vs_2024(tmp_path, monkeypatch):
    """Comparaison N/N-1 sur Les Acacias detecte les evolutions."""
    import historique_manager, historique_demo
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    for entree in historique_demo.DEMO_HISTORIQUE:
        historique_manager.sauvegarder_ag(entree["analyse"])
    dossiers = historique_manager.lister_dossiers()
    dossier_acacias = next(d for d in dossiers if "Acacias" in d["entite"])
    ag_acacias = historique_manager.lister_ag(dossier=dossier_acacias["dossier"])
    # Trier par date de sauvegarde
    ag_acacias_tri = sorted(ag_acacias, key=lambda x: x["sauvegarde_le"])
    rapport = historique_manager.comparer_ag(ag_acacias_tri[0]["fichier"], ag_acacias_tri[1]["fichier"])
    # Les 2 AG ont des resolutions communes (Comptes, Budget, Chaudiere)
    assert len(rapport["resolutions_communes"]) >= 2
    # 2024 a une resolution de plus (Ravalement)
    assert len(rapport["nouvelles_resolutions"]) >= 1


def test_acacias_2023_chaudiere_rejetee():
    """En 2023, la resolution chaudiere est rejetee."""
    import historique_demo
    res_chaudiere = next(r for r in historique_demo.AG_ACACIAS_2023["resolutions"] if "chaudiere" in r["titre"].lower())
    assert res_chaudiere["statut"] == "rejetee"


def test_acacias_2024_chaudiere_rejetee_2eme_fois():
    """En 2024, la resolution chaudiere est rejetee pour la 2eme fois."""
    import historique_demo
    res_chaudiere = next(r for r in historique_demo.AG_ACACIAS_2024["resolutions"] if "chaudiere" in r["titre"].lower())
    assert res_chaudiere["statut"] == "rejetee"
    assert "2eme" in res_chaudiere["description"].lower() or "deuxieme" in res_chaudiere["description"].lower()


def test_acacias_2024_plus_de_participants_que_2023():
    """En 2024, il y a plus de participants qu en 2023 (14 vs 12)."""
    import historique_demo
    assert historique_demo.AG_ACACIAS_2024["participants"]["total_presents"] > historique_demo.AG_ACACIAS_2023["participants"]["total_presents"]


def test_export_dossier_acacias_uniquement(tmp_path, monkeypatch):
    """Export du seul dossier Acacias produit un ZIP avec 2 fichiers."""
    import historique_manager, historique_demo, zipfile, io
    monkeypatch.setattr(historique_manager, "HISTORIQUE_DIR", tmp_path)
    for entree in historique_demo.DEMO_HISTORIQUE:
        historique_manager.sauvegarder_ag(entree["analyse"])
    dossiers = historique_manager.lister_dossiers()
    dossier_acacias = next(d for d in dossiers if "Acacias" in d["entite"])
    zip_bytes = historique_manager.exporter_historique(dossier=dossier_acacias["dossier"])
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        assert len(zf.namelist()) == 2
