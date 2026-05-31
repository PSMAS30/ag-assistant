"""
app.py — Assistant AG | Interface professionnelle de gestion d assemblees generales
Architecture : Dashboard "Mes AG" + Workflow 7 etapes par AG
"""

import os
import json
import tempfile
from datetime import datetime
from collections import defaultdict
import streamlit as st
from dotenv import load_dotenv

import demo_data
import analyzer
import pv_generator
import word_generator
import historique_manager
import historique_demo
import convocation_generator
import presence_generator

try:
    import faster_whisper
    import transcriber
    TRANSCRIPTION_DISPONIBLE = True
except ImportError:
    TRANSCRIPTION_DISPONIBLE = False

load_dotenv()

# ─── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Assistant AG", page_icon="🏛️", layout="wide", initial_sidebar_state="collapsed")

# ─── Session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "vue": "dashboard", "ag_active": None, "etape": 1, "etapes_ok": [],
    "transcription": None, "segments": None, "segments_diarises": None,
    "locuteurs": None, "mapping_locuteurs": None, "analyse": None,
    "pv_texte": None, "demo_key": None, "historique_fichier_actuel": None,
    "demo_historique_session": [],
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── Constantes ────────────────────────────────────────────────────────────────
STEPS = [("📬","Convocation"),("👥","Présence"),("🎙️","Réunion"),("📋","Analyse"),("📄","PV"),("✍️","Signature"),("🗂️","Archivage")]
TYPES_AG = {"copropriete":"🏢 Copropriété","association":"🤝 Association","pme_sas":"🏭 SAS","pme_sarl":"🏭 SARL","pme_autre":"🏭 PME","autre":"📋 Autre"}

# ─── Helpers ───────────────────────────────────────────────────────────────────
def _nav(vue, **kw):
    st.session_state.vue = vue
    for k, v in kw.items():
        st.session_state[k] = v
    st.rerun()

def _statut_ag(entree):
    meta = entree.get("meta_historique", {})
    if meta.get("signature_date"): return 7, "✅ Signé"
    if entree.get("pv_texte"): return 6, "📄 PV généré"
    a = entree.get("analyse", {})
    if a and a.get("resolutions"): return 5, "📋 Analysé"
    if entree.get("transcription"): return 4, "🎙️ Transcrit"
    return 1, "🆕 Nouveau"

def _charger_session(fichier):
    e = historique_manager.charger_ag(fichier)
    st.session_state.ag_active = e
    st.session_state.analyse = e.get("analyse", {})
    st.session_state.pv_texte = e.get("pv_texte")
    st.session_state.transcription = e.get("transcription", "")
    st.session_state.historique_fichier_actuel = fichier
    etape, _ = _statut_ag(e)
    st.session_state.etape = min(etape, 7)
    st.session_state.etapes_ok = list(range(1, etape))

def _analyse_simulee(demo):
    m = demo.get("metadata", {})
    nb_p = m.get("nb_presents", 0) or 0
    nb_r = m.get("nb_representes", 0) or 0
    return {
        "meta": {"version":"2.0","genere_par":"demo","niveau_confiance_global":"demo","avertissement":"Données de démonstration."},
        "type_ag": m.get("type","autre"),
        "informations_generales": {"entite":m.get("nom","Demo"),"date":m.get("date",""),"lieu":m.get("lieu",""),"type_assemblee":"AG ordinaire annuelle","heure_ouverture":"","heure_cloture":"","president_seance":m.get("president",m.get("syndic","")),"secretaire":"","scrutateurs":[]},
        "participants": {"presents":[{"nom":f"{nb_p} présents","qualite":"membre","voix_ou_parts":None,"observations":""}],"representes":[],"absents_excuses":[],"total_presents":nb_p,"total_representes":nb_r,"total_votants":nb_p+nb_r,"total_voix":nb_p+nb_r,"quorum_requis":"Selon statuts","quorum_calcule":None,"quorum_atteint":True,"base_legale_quorum":"","observations_quorum":"Demo"},
        "ordre_du_jour":[],"resolutions":[],"decisions_finales":[],"points_divers":["[Demo]"],
        "conformite_legale":{"mentions_obligatoires_pv":{},"alertes":[],"recommandations":[]},
        "observations_juridiques":"Demo.","niveaux_confiance_sections":{},"diarization":[],
    }

# ─── Sidebar ───────────────────────────────────────────────────────────────────
def _sidebar():
    with st.sidebar:
        st.title("🏛️ Assistant AG")
        st.caption("Gestion d assemblees generales françaises")
        st.divider()
        mode = st.radio("Mode", ["🎭 Demo (sans cle API)", "🔑 Avec ma cle API"], index=0, key="mode_global")
        api_key = hf_token_ui = None
        if mode == "🔑 Avec ma cle API":
            st.caption("🔐 Clés utilisées en session uniquement.")
            api_key = st.text_input("Clé API Anthropic", type="password", placeholder="sk-ant-...", key="api_key_input")
            if not api_key: st.warning("Clé API requise pour l analyse.")
            hf_token_ui = st.text_input("Token HuggingFace (diarization)", type="password", placeholder="hf_...", key="hf_token_input")
        st.divider()
        if st.session_state.vue != "dashboard":
            if st.button("🏠 Mes Assemblées Générales", use_container_width=True):
                _nav("dashboard")
        st.caption("📂 [Code source](https://github.com/PSMAS30/ag-assistant)")
        st.caption("🛠️ faster-whisper · Claude · Streamlit")
    return mode, api_key, hf_token_ui

# ══════════════════════════════════════════════════════════════════════════════
# VUE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def _dashboard():
    col_t, col_b = st.columns([4, 1])
    with col_t: st.title("🏛️ Mes Assemblées Générales")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Nouvelle AG", type="primary", use_container_width=True):
            _nav("nouvelle_ag")

    # ── Bandeau demo guidee ──────────────────────────────────────────────────
    st.info(
        "🎭 **Découvrez le workflow complet** — Parcourez les 7 étapes avec une AG fictive pré-remplie, sans clé API ni fichier audio.   "
        "  ​"
    )
    if st.button("▶️ Lancer la démo guidée (Copropriété Les Acacias — 7 étapes)", type="secondary", use_container_width=True, key="btn_demo_guidee"):
        _lancer_demo_guidee()
    st.divider()

    demo_session = st.session_state.demo_historique_session
    dossiers = historique_manager.lister_dossiers()
    nb_disk = historique_manager.nb_ag_sauvegardees()

    # ── Aucune donnee ────────────────────────────────────────────────────────
    if not demo_session and nb_disk == 0:
        st.info("Aucune assemblée générale enregistrée. Cliquez sur **➕ Nouvelle AG** pour commencer.")
        return

    # ── Section demo session ─────────────────────────────────────────────────
    if demo_session:
        demo_par_entite = defaultdict(list)
        for e in demo_session:
            entite = e["analyse"].get("informations_generales", {}).get("entite", "Demo")
            demo_par_entite[entite].append(e)
        for entite, entrees in demo_par_entite.items():
            type_ag = entrees[0]["analyse"].get("type_ag", "autre")
            with st.expander(f"🎭 **{entite}**  ·  {TYPES_AG.get(type_ag,type_ag)}  ·  {len(entrees)} AG  *(session demo)*", expanded=True):
                for i, e in enumerate(entrees):
                    infos = e["analyse"].get("informations_generales", {})
                    date = infos.get("date", "date inconnue")
                    nb_r = len(e["analyse"].get("resolutions", []))
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**AG du {date}**  ·  {nb_r} résolution(s)")
                    c2.caption("🎭 Demo session")
                    with c3:
                        if st.button("Ouvrir →", key=f"open_demo_{entite}_{i}", use_container_width=True):
                            st.session_state.analyse = e["analyse"]
                            st.session_state.pv_texte = e.get("pv_texte")
                            st.session_state.transcription = ""
                            st.session_state.ag_active = {"meta_historique":{"entite":entite,"type_ag":type_ag,"date_ag":date,"is_demo_session":True},"analyse":e["analyse"],"pv_texte":e.get("pv_texte")}
                            st.session_state.etape = 4
                            st.session_state.etapes_ok = [1, 2, 3]
                            st.session_state.historique_fichier_actuel = None
                            _nav("workflow")
        if st.button("🗑️ Vider la demo session", key="btn_vider_demo"):
            st.session_state.demo_historique_session = []
            st.rerun()
        st.divider()

    # ── AG reelles (disque) ──────────────────────────────────────────────────
    if nb_disk > 0:
        for dos in dossiers:
            ag_list = historique_manager.lister_ag(dossier=dos["dossier"])
            type_label = TYPES_AG.get(ag_list[0]["type_ag"] if ag_list else "autre", "")
            with st.expander(f"📁 **{dos['entite']}**  ·  {type_label}  ·  {dos['nb_ag']} AG", expanded=True):
                for ag in ag_list:
                    try:
                        e2 = historique_manager.charger_ag(ag["fichier"])
                        etape_e, badge = _statut_ag(e2)
                    except Exception:
                        etape_e, badge = 1, "?"
                    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                    c1.markdown(f"**AG du {ag['date_ag'] or '?'}**  ·  {ag['nb_resolutions']} résolution(s)")
                    c2.caption(badge)
                    c3.caption(f"Étape {etape_e}/7")
                    with c4:
                        if st.button("Ouvrir →", key=f"open_{ag['nom_fichier']}", use_container_width=True):
                            _charger_session(ag["fichier"])
                            _nav("workflow")

    # ── Loader demo ──────────────────────────────────────────────────────────
    with st.expander("🎭 Données de démonstration"):
        st.caption("Éphémère — disparaît au rechargement de page")
        if st.button("📥 Charger les 4 AG demo", key="btn_demo_bottom"):
            _charger_demo()

def _charger_demo():
    existantes = {(e["analyse"].get("informations_generales",{}).get("entite",""), e["analyse"].get("informations_generales",{}).get("date","")) for e in st.session_state.demo_historique_session}
    nb = 0
    for e in historique_demo.DEMO_HISTORIQUE:
        infos = e["analyse"].get("informations_generales", {})
        if (infos.get("entite",""), infos.get("date","")) not in existantes:
            st.session_state.demo_historique_session.append(e)
            nb += 1
    if nb: st.success(f"{nb} AG demo chargées ✅"); st.rerun()
    else: st.info("Données demo déjà présentes.")


def _lancer_demo_guidee():
    """
    Lance la demo guidee : charge la Copropriete Les Acacias 2024
    avec toutes les donnees pre-remplies (transcription + analyse + PV demo)
    et demarre au workflow etape 1.
    """
    # Analyse pre-remplie depuis historique_demo
    analyse = historique_demo.AG_ACACIAS_2024

    # Transcription pre-remplie depuis demo_data
    transcription = demo_data.get_demo("copropriete")["transcription"].strip()

    # PV genere en mode demo (sans API)
    pv_texte = pv_generator.pv_demo(analyse)

    # Metadonnees
    meta = {
        "entite": "Copropriété Les Acacias",
        "dossier": "Copropriete_Les_Acacias",
        "type_ag": "copropriete",
        "date_ag": "15/06/2024",
        "lieu": "Salle communale, 12 rue des Lilas, 75012 Paris",
        "is_demo_session": True,
        "is_demo_guidee": True,
        "sauvegarde_le": "",
        "nb_resolutions": len(analyse.get("resolutions", [])),
        "a_pv": True,
        "audit_trail": [],
    }

    st.session_state.ag_active = {"meta_historique": meta, "analyse": analyse, "pv_texte": pv_texte, "transcription": transcription}
    st.session_state.analyse = analyse
    st.session_state.transcription = transcription
    st.session_state.pv_texte = pv_texte
    st.session_state.segments = None
    st.session_state.historique_fichier_actuel = None
    st.session_state.etape = 1          # ← commence a l etape 1
    st.session_state.etapes_ok = []     # ← aucune etape marquee OK
    _nav("workflow")

# ══════════════════════════════════════════════════════════════════════════════
# VUE 2 — NOUVELLE AG
# ══════════════════════════════════════════════════════════════════════════════
def _nouvelle_ag():
    if st.button("← Retour"): _nav("dashboard")
    st.title("➕ Nouvelle Assemblée Générale")
    st.divider()
    with st.form("form_nouvelle_ag"):
        c1, c2 = st.columns(2)
        with c1:
            entite = st.text_input("Nom de l entité *", placeholder="Ex : Copropriété Les Lilas")
            type_ag = st.selectbox("Type *", list(TYPES_AG.keys()), format_func=lambda k: TYPES_AG[k])
        with c2:
            date_ag = st.text_input("Date prévue", placeholder="JJ/MM/AAAA")
            lieu = st.text_input("Lieu", placeholder="Adresse ou salle")
        notes = st.text_area("Notes / contexte", height=80)
        ok = st.form_submit_button("Créer cette AG →", type="primary")
    if ok and entite:
        analyse_vide = {
            "type_ag": type_ag,
            "informations_generales": {"entite":entite,"date":date_ag,"lieu":lieu,"type_assemblee":"AG ordinaire annuelle","heure_ouverture":"","heure_cloture":"","president_seance":"","secretaire":"","scrutateurs":[]},
            "participants": {"presents":[],"representes":[],"absents_excuses":[],"total_presents":None,"total_representes":None,"total_votants":None,"total_voix":None,"quorum_requis":"","quorum_calcule":None,"quorum_atteint":None,"base_legale_quorum":"","observations_quorum":""},
            "ordre_du_jour":[],"resolutions":[],"decisions_finales":[],"points_divers":[],
            "conformite_legale":{"mentions_obligatoires_pv":{},"alertes":[],"recommandations":[]},
            "observations_juridiques":"","niveaux_confiance_sections":{},"diarization":[],
        }
        st.session_state.ag_active = {"meta_historique":{"entite":entite,"dossier":historique_manager._nom_dossier(entite),"type_ag":type_ag,"date_ag":date_ag,"lieu":lieu,"notes":notes,"sauvegarde_le":datetime.now().isoformat(),"nb_resolutions":0,"a_pv":False,"audit_trail":[]},"analyse":analyse_vide,"pv_texte":None,"transcription":""}
        st.session_state.analyse = analyse_vide
        st.session_state.pv_texte = None
        st.session_state.transcription = ""
        st.session_state.etape = 1
        st.session_state.etapes_ok = []
        st.session_state.historique_fichier_actuel = None
        _nav("workflow")
    elif ok: st.warning("Le nom de l entité est obligatoire.")

# ══════════════════════════════════════════════════════════════════════════════
# VUE 3 — WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════
def _step_bar(etape, etapes_ok):
    cols = st.columns(len(STEPS))
    for i, (col, (ic, nom)) in enumerate(zip(cols, STEPS), 1):
        if i in etapes_ok:
            col.markdown(f"<div style='text-align:center;color:#28a745;font-size:.85em'>{ic}<br>✅ {nom}</div>", unsafe_allow_html=True)
        elif i == etape:
            col.markdown(f"<div style='text-align:center;color:#0066cc;font-weight:bold;font-size:.85em;border-bottom:3px solid #0066cc;padding-bottom:3px'>{ic}<br>▶ {nom}</div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div style='text-align:center;color:#aaa;font-size:.85em'>{ic}<br>{nom}</div>", unsafe_allow_html=True)
    st.markdown("---")

def _nav_btns(etape, etapes_ok, label="Étape suivante →", can_next=True):
    c1, _, c3 = st.columns([1, 3, 1])
    with c1:
        if etape > 1 and st.button("← Précédent", key=f"prev_{etape}", use_container_width=True):
            st.session_state.etape = etape - 1; st.rerun()
    with c3:
        if etape < 7 and can_next:
            if st.button(label, key=f"next_{etape}", type="primary", use_container_width=True):
                if etape not in etapes_ok: etapes_ok.append(etape)
                st.session_state.etapes_ok = etapes_ok
                st.session_state.etape = etape + 1; st.rerun()

def _workflow(mode, api_key, hf_token_ui):
    ag = st.session_state.ag_active or {}
    meta = ag.get("meta_historique", {})
    entite = meta.get("entite", "Assemblée Générale")
    date_ag = meta.get("date_ag", "")
    type_ag = meta.get("type_ag", "autre")
    is_demo_guidee = meta.get("is_demo_guidee", False)
    etape = st.session_state.etape
    etapes_ok = st.session_state.etapes_ok

    # Banniere demo guidee
    if is_demo_guidee:
        st.success(
            "🎭 **Mode démo guidée** — Toutes les données sont pré-remplies. "
            "Naviguez librement les 7 étapes : convocation, présence, transcription, analyse, PV, signature, archivage. "
            "Aucune clé API requise."
        )

    cb, ct, _ = st.columns([1, 5, 1])
    with cb:
        if st.button("← Retour", key="back_wf"): _nav("dashboard")
    with ct:
        st.markdown(f"## 🏛️ {entite}")
        st.caption(f"{TYPES_AG.get(type_ag, type_ag)}  ·  {date_ag or 'date non définie'}{'  ·  🎭 Demo' if is_demo_guidee else ''}")

    _step_bar(etape, etapes_ok)

    # Nav rapide sidebar
    with st.sidebar:
        st.divider()
        st.caption("Navigation rapide")
        for i, (ic, nom) in enumerate(STEPS, 1):
            s = "✅" if i in etapes_ok else ("▶" if i == etape else "○")
            if st.button(f"{s} {i}. {ic} {nom}", key=f"nav_{i}", use_container_width=True):
                st.session_state.etape = i; st.rerun()

    if etape == 1: _s1_convocation(ag, meta, etape, etapes_ok, api_key)
    elif etape == 2: _s2_presence(ag, meta, etape, etapes_ok)
    elif etape == 3: _s3_reunion(ag, meta, etape, etapes_ok, mode, api_key, hf_token_ui)
    elif etape == 4: _s4_analyse(ag, meta, etape, etapes_ok, mode, api_key)
    elif etape == 5: _s5_pv(ag, meta, etape, etapes_ok, api_key)
    elif etape == 6: _s6_signature(ag, meta, etape, etapes_ok)
    elif etape == 7: _s7_archivage(ag, meta, etape, etapes_ok)

# ── S1 Convocation ─────────────────────────────────────────────────────────────
def _s1_convocation(ag, meta, etape, etapes_ok, api_key):
    st.subheader("📬 Étape 1 — Convocation")
    st.caption("Générez la convocation légale à envoyer aux membres avant la réunion.")
    analyse = st.session_state.analyse or ag.get("analyse", {})
    c1, c2 = st.columns(2)
    with c1:
        date_c = st.date_input("Date d envoi", value=datetime.now(), key="conv_date")
        date_ag_p = st.text_input("Date de l AG", value=meta.get("date_ag",""), placeholder="JJ/MM/AAAA", key="conv_dag")
    with c2:
        lieu = st.text_input("Lieu", value=meta.get("lieu", analyse.get("informations_generales",{}).get("lieu","")), key="conv_lieu")
    if st.button("Générer la convocation", type="primary", key="btn_conv"):
        ds = date_c.strftime("%d/%m/%Y") if date_c else None
        ca, cb2 = st.columns(2)
        with ca:
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t: tmp = t.name
                convocation_generator.generer_convocation_pdf(analyse, tmp, ds, date_ag_p or None, lieu or None)
                with open(tmp, "rb") as f: st.download_button("📥 Convocation PDF", f.read(), "convocation_ag.pdf", "application/pdf", key="dl_conv_pdf")
            except Exception as e: st.error(f"PDF : {e}")
            finally:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
        with cb2:
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as t: tmp = t.name
                convocation_generator.generer_convocation_word(analyse, tmp, ds, date_ag_p or None, lieu or None)
                with open(tmp, "rb") as f: st.download_button("📥 Convocation Word", f.read(), "convocation_ag.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_conv_word")
            except Exception as e: st.error(f"Word : {e}")
            finally:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
    _nav_btns(etape, etapes_ok, "Préparer la présence →")

# ── S2 Présence ────────────────────────────────────────────────────────────────
def _s2_presence(ag, meta, etape, etapes_ok):
    st.subheader("👥 Étape 2 — Feuille de présence")
    st.caption("Générez la feuille de présence à faire signer lors de la réunion.")
    analyse = st.session_state.analyse or ag.get("analyse", {})
    p = analyse.get("participants", {})
    if p.get("total_votants"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Présents", p.get("total_presents","—"))
        c2.metric("Représentés", p.get("total_representes","—"))
        c3.metric("Total votants", p.get("total_votants","—"))
    if st.button("Générer la feuille de présence", type="primary", key="btn_pres"):
        ca, cb = st.columns(2)
        with ca:
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t: tmp = t.name
                presence_generator.generer_feuille_presence_pdf(analyse, tmp)
                with open(tmp, "rb") as f: st.download_button("📥 Présence PDF", f.read(), "feuille_presence.pdf", "application/pdf", key="dl_pres_pdf")
            except Exception as e: st.error(f"PDF : {e}")
            finally:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
        with cb:
            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as t: tmp = t.name
                presence_generator.generer_feuille_presence_word(analyse, tmp)
                with open(tmp, "rb") as f: st.download_button("📥 Présence Word", f.read(), "feuille_presence.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_pres_word")
            except Exception as e: st.error(f"Word : {e}")
            finally:
                if tmp and os.path.exists(tmp): os.unlink(tmp)
    _nav_btns(etape, etapes_ok, "Enregistrer la réunion →")

# ── S3 Réunion ─────────────────────────────────────────────────────────────────
def _s3_reunion(ag, meta, etape, etapes_ok, mode, api_key, hf_token_ui):
    st.subheader("🎙️ Étape 3 — Réunion")
    st.caption("Chargez l enregistrement audio ou utilisez une AG de démonstration.")

    # Demo guidee : transcription deja pre-chargee
    if meta.get("is_demo_guidee") and st.session_state.transcription:
        st.success("✅ Transcription pré-chargée (demo Copropriété Les Acacias)")
        st.text_area("Transcription", value=st.session_state.transcription, height=200, key="s3_txte_demo", disabled=True)
        _nav_btns(etape, etapes_ok, "Analyser l AG →", can_next=True)
        return

    if not TRANSCRIPTION_DISPONIBLE:
        st.warning("⚠️ **Transcription non disponible sur cette instance.** Utilisez le mode demo ou installez l app en local.")
    opts = ["📁 Fichier audio", "🎭 AG de demo"] if TRANSCRIPTION_DISPONIBLE else ["🎭 AG de demo"]
    src = st.radio("Source", opts, horizontal=True, key="s3_src")
    if src == "🎭 AG de demo":
        demos = demo_data.list_demos()
        choix = st.selectbox("AG de demo", [d["key"] for d in demos], format_func=lambda k: next(d["label"] for d in demos if d["key"] == k), key="s3_demo_choix")
        if st.button("Charger cette demo", type="primary", key="btn_s3_demo"):
            d = demo_data.get_demo(choix)
            st.session_state.transcription = d["transcription"].strip()
            st.session_state.segments = None
            st.session_state.demo_key = choix
            st.success("Transcription demo chargée ✅")
    elif src == "📁 Fichier audio" and TRANSCRIPTION_DISPONIBLE:
        fichier = st.file_uploader("Fichier audio", type=["mp3","wav","m4a","ogg","flac"], key="s3_audio")
        ca, cb = st.columns(2)
        with ca: modele = st.select_slider("Précision", options=transcriber.MODELES_DISPONIBLES, value=transcriber.MODELE_DEFAUT, key="s3_modele")
        with cb:
            diar = st.toggle("🗣️ Diarization", key="s3_diar")
            if diar: nb_loc = st.number_input("Nb locuteurs (0=auto)", 0, 20, 0, key="s3_nb_loc")
        if fichier and st.button("Transcrire", type="primary", key="btn_s3_trans"):
            suffix = "." + fichier.name.rsplit(".",1)[-1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as t:
                t.write(fichier.read()); tp = t.name
            try:
                if diar:
                    hf = hf_token_ui or os.getenv("HF_TOKEN","")
                    if not hf: st.error("Token HF requis."); st.stop()
                    with st.spinner("Transcription + diarization…"):
                        res = transcriber.transcrire_avec_diarization(tp, modele=modele, hf_token=hf, nb_locuteurs=int(nb_loc) if nb_loc > 0 else None)
                    st.session_state.transcription = res["texte"]
                    st.session_state.segments = res.get("segments",[])
                    st.session_state.segments_diarises = res.get("segments_diarises",[])
                    st.session_state.locuteurs = res.get("locuteurs",[])
                    st.session_state.mapping_locuteurs = {l:l for l in res.get("locuteurs",[])}
                    st.success(f"✅ {res.get('duree_secondes')}s — {len(res.get('locuteurs',[]))} locuteurs")
                else:
                    with st.spinner("Transcription…"):
                        res = transcriber.transcrire_audio(tp, modele=modele)
                    st.session_state.transcription = res["texte"]
                    st.session_state.segments = res.get("segments",[])
                    st.session_state.segments_diarises = None
                    st.success(f"✅ Transcription terminée ({res.get('duree_secondes')}s)")
            except Exception as e: st.error(f"Erreur : {e}")
            finally: os.unlink(tp)
    if st.session_state.transcription:
        st.divider()
        txte = st.text_area("Transcription (éditable)", value=st.session_state.transcription, height=250, key="s3_txte")
        if txte != st.session_state.transcription: st.session_state.transcription = txte
        segs = st.session_state.segments
        if segs:
            with st.expander(f"⏱️ Segments ({len(segs)})"):
                for seg in segs:
                    def fmt(s):
                        if s is None: return "—"
                        m, s2 = divmod(int(s), 60); return f"{m:02d}:{s2:02d}"
                    st.markdown(f"`{fmt(seg.get('debut'))} → {fmt(seg.get('fin'))}` {seg.get('texte','')}")
        segs_d = st.session_state.segments_diarises
        locs = st.session_state.locuteurs
        if segs_d and locs:
            with st.expander("🗣️ Renommer les locuteurs", expanded=True):
                mapping = st.session_state.mapping_locuteurs or {l:l for l in locs}
                new_map = {}
                cols = st.columns(2)
                for i, loc in enumerate(locs):
                    with cols[i % 2]: new_map[loc] = st.text_input(f"Nom pour {loc}", value=mapping.get(loc,loc), key=f"loc_{loc}")
                if st.button("Appliquer", key="btn_locs"):
                    st.session_state.mapping_locuteurs = new_map
                    sr = transcriber.renommer_locuteurs(segs_d, new_map)
                    st.session_state.segments_diarises = sr
                    st.session_state.transcription = transcriber.segments_diarises_vers_texte(sr)
                    st.success("Noms appliqués ✅"); st.rerun()
    _nav_btns(etape, etapes_ok, "Analyser l AG →", can_next=bool(st.session_state.transcription))

# ── S4 Analyse ─────────────────────────────────────────────────────────────────
def _s4_analyse(ag, meta, etape, etapes_ok, mode, api_key):
    st.subheader("📋 Étape 4 — Analyse")
    st.caption("Claude extrait résolutions, votes, quorum et vérifie la conformité légale.")
    a = st.session_state.analyse
    has_trans = bool(st.session_state.transcription)
    has_ana = bool(a and a.get("resolutions") is not None)
    cle = api_key or os.getenv("ANTHROPIC_API_KEY","")
    if has_trans:
        if not cle: st.info("Entrez votre clé API dans la barre latérale pour analyser.")
        else:
            if st.button("Analyser l AG avec Claude", type="primary", key="btn_ana"):
                with st.spinner("Analyse en cours…"):
                    try:
                        st.session_state.analyse = analyzer.analyser_transcription(st.session_state.transcription, cle)
                        a = st.session_state.analyse
                        st.success("Analyse terminée ✅")
                    except Exception as e: st.error(f"Erreur : {e}")
    elif not has_ana:
        st.info("Chargez d abord une transcription (étape 3).")
    if a and a.get("resolutions") is not None:
        meta_a = a.get("meta",{})
        if meta_a.get("avertissement"): st.warning(f"⚠️ {meta_a['avertissement']}")
        infos = a.get("informations_generales",{})
        p2 = a.get("participants",{})
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Type", a.get("type_ag","—").replace("_"," ").capitalize())
        c2.metric("Votants", p2.get("total_votants","—"))
        qr = p2.get("quorum_atteint")
        c3.metric("Quorum", "✅ Atteint" if qr is True else "❌ Non atteint" if qr is False else "—")
        c4.metric("Confiance IA", meta_a.get("niveau_confiance_global","—").capitalize())
        st.subheader(f"{infos.get('entite','')} — {infos.get('date','')}")
        conf = a.get("niveaux_confiance_sections",{})
        if conf and any(isinstance(conf.get(k),(int,float)) for k in ["participants","votes","quorum"]):
            with st.expander("📊 Confiance par section", expanded=True):
                secs = [("Participants",conf.get("participants")),("Votes",conf.get("votes")),("Quorum",conf.get("quorum")),("Convocation",conf.get("convocation")),("Ordre du jour",conf.get("ordre_du_jour"))]
                valid = [(l,s) for l,s in secs if s is not None]
                cols = st.columns(len(valid))
                for i,(label,score) in enumerate(valid):
                    ic = "✅" if score>=90 else "⚠️" if score>=70 else "❌"
                    cols[i].metric(label, f"{ic} {score}%"); cols[i].progress(int(score)/100)
        resolutions = a.get("resolutions",[])
        if resolutions:
            st.subheader(f"Résolutions ({len(resolutions)})")
            for r in resolutions:
                statut = r.get("statut","")
                ic = "✅" if statut=="adoptée" else "❌" if statut=="rejetée" else "⚠️"
                ts = r.get("timestamps",{})
                src_lbl = f"  ·  ⏱ {ts.get('debut')} → {ts.get('fin')}" if ts.get("debut") and ts.get("fin") else ""
                with st.expander(f"{ic} R{r.get('numero')} — {r.get('titre',r.get('intitule',''))}{src_lbl}"):
                    st.write(r.get("description",""))
                    if ts.get("debut") and ts.get("fin"): st.markdown(f"**Source audio :** `{ts['debut']}` → `{ts['fin']}`")
                    votes = r.get("votes",{}); unite = votes.get("unite","voix")
                    cx,cy,cz = st.columns(3)
                    cx.metric("Pour", f"{votes.get('pour','—')} {unite}")
                    cy.metric("Contre", f"{votes.get('contre','—')} {unite}")
                    cz.metric("Abstentions", f"{votes.get('abstentions',votes.get('abstention','—'))} {unite}")
                    if r.get("base_legale"): st.caption(f"Base légale : {r['base_legale']}")
        conf_leg = a.get("conformite_legale",{})
        if conf_leg.get("alertes"):
            with st.expander("⚖️ Alertes de conformité"):
                for al in conf_leg["alertes"]: st.write(f"🔴 {al}")
        with st.expander("🔍 JSON brut"): st.json(a)
    _nav_btns(etape, etapes_ok, "Générer le PV →", can_next=has_ana or bool(a and a.get("resolutions") is not None))

# ── S5 PV ──────────────────────────────────────────────────────────────────────
def _s5_pv(ag, meta, etape, etapes_ok, api_key):
    st.subheader("📄 Étape 5 — Procès-verbal")
    st.caption("Générez, corrigez et exportez le PV en PDF, Word ou TXT.")
    analyse = st.session_state.analyse or {}
    cle = api_key or os.getenv("ANTHROPIC_API_KEY","")
    if st.button("Générer le PV", type="primary", key="btn_pv"):
        if cle:
            with st.spinner("Rédaction par Claude…"):
                try:
                    st.session_state.pv_texte = pv_generator.generer_pv_texte(analyse, cle)
                    fic = st.session_state.historique_fichier_actuel
                    if fic: historique_manager.ajouter_action_audit(fic, "pv_genere", (st.session_state.pv_texte or "")[:80])
                    st.success("PV généré ✅")
                except Exception as e: st.error(f"Erreur : {e}")
        else:
            st.session_state.pv_texte = pv_generator.pv_demo(analyse)
            st.success("PV généré (mode demo) ✅")
    if st.session_state.pv_texte:
        pv_e = st.text_area("Procès-verbal (éditable)", value=st.session_state.pv_texte, height=400, key="pv_edit")
        if pv_e != st.session_state.pv_texte: st.session_state.pv_texte = pv_e
        st.divider()
        st.caption("📥 Exporter")
        c1,c2,c3 = st.columns(3)
        with c1: st.download_button("⬇️ TXT", data=st.session_state.pv_texte.encode("utf-8"), file_name="pv_ag.txt", mime="text/plain", key="dl_pv_txt")
        with c2:
            if st.button("⬇️ PDF", key="btn_pv_pdf2", use_container_width=True):
                tmp = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as t: tmp=t.name
                    pv_generator.exporter_pv_pdf(st.session_state.pv_texte, tmp)
                    with open(tmp,"rb") as f: st.download_button("📥 PDF", f.read(), "pv_ag.pdf", "application/pdf", key="dl_pv_pdf3")
                except Exception as e: st.error(f"Erreur PDF : {e}")
                finally:
                    if tmp and os.path.exists(tmp):
                        try: os.unlink(tmp)
                        except: pass
        with c3:
            if st.button("⬇️ Word", key="btn_pv_word2", use_container_width=True):
                tmp = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".docx",delete=False) as t: tmp=t.name
                    word_generator.generer_pv_word(analyse, tmp)
                    with open(tmp,"rb") as f: st.download_button("📥 Word", f.read(), "pv_ag.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_pv_word3")
                except Exception as e: st.error(f"Erreur Word : {e}")
                finally:
                    if tmp and os.path.exists(tmp):
                        try: os.unlink(tmp)
                        except: pass
    _nav_btns(etape, etapes_ok, "Signature →", can_next=bool(st.session_state.pv_texte))

# ── S6 Signature ───────────────────────────────────────────────────────────────
def _s6_signature(ag, meta, etape, etapes_ok):
    st.subheader("✍️ Étape 6 — Signature")
    st.caption("Enregistrez la validation du PV par les signataires.")
    sig = (ag or {}).get("meta_historique", {}).get("signature_date")
    if sig: st.success(f"✅ PV signé le {sig}")
    else: st.info("Le PV doit être signé physiquement par le président de séance et le secrétaire avant d avoir valeur juridique.")
    with st.form("form_sig"):
        c1,c2 = st.columns(2)
        with c1:
            signe_par = st.text_input("Signé par (président)", placeholder="Prénom Nom")
            date_s = st.date_input("Date de signature", value=datetime.now())
        with c2:
            secretaire = st.text_input("Secrétaire", placeholder="Prénom Nom")
            notes_s = st.text_area("Notes", height=80)
        ok = st.form_submit_button("Marquer comme signé ✅", type="primary")
    if ok:
        fic = st.session_state.historique_fichier_actuel
        if fic:
            try:
                e = historique_manager.charger_ag(fic)
                e["meta_historique"].update({"signature_date":date_s.strftime("%d/%m/%Y"),"signature_par":signe_par,"secretaire":secretaire,"signature_notes":notes_s})
                with open(fic,"w",encoding="utf-8") as f: json.dump(e,f,ensure_ascii=False,indent=2)
                historique_manager.ajouter_action_audit(fic,"pv_signe",f"Signé par {signe_par} le {date_s.strftime('%d/%m/%Y')}")
                st.session_state.ag_active = e
                st.success("PV marqué comme signé ✅")
            except Exception as e2: st.error(f"Erreur : {e2}")
        if etape not in etapes_ok: etapes_ok.append(etape)
        st.session_state.etapes_ok = etapes_ok; st.rerun()
    _nav_btns(etape, etapes_ok, "Archiver →")

# ── S7 Archivage ───────────────────────────────────────────────────────────────
def _s7_archivage(ag, meta, etape, etapes_ok):
    st.subheader("🗂️ Étape 7 — Archivage")
    st.caption("Sauvegardez cette AG dans votre historique.")
    analyse = st.session_state.analyse or {}
    pv_texte = st.session_state.pv_texte
    entite = meta.get("entite","Entite")
    fic = st.session_state.historique_fichier_actuel
    if fic:
        st.success(f"✅ AG archivée — dossier : **{meta.get('dossier', entite)}**")
        if pv_texte and st.button("Mettre à jour le PV dans l archive", key="btn_upd_pv"):
            try:
                e = historique_manager.charger_ag(fic)
                e["pv_texte"] = pv_texte; e["meta_historique"]["a_pv"] = True
                with open(fic,"w",encoding="utf-8") as f: json.dump(e,f,ensure_ascii=False,indent=2)
                historique_manager.ajouter_action_audit(fic,"pv_archive","PV mis à jour")
                st.success("Archive mise à jour ✅")
            except Exception as e2: st.error(f"Erreur : {e2}")
    else:
        st.info(f"Cette AG sera sauvegardée dans le dossier **{historique_manager._nom_dossier(entite)}**.")
        if st.button("📦 Archiver cette AG", type="primary", key="btn_arch"):
            try:
                chemin = historique_manager.sauvegarder_ag(analyse, pv_texte)
                st.session_state.historique_fichier_actuel = chemin
                if etape not in etapes_ok: etapes_ok.append(etape)
                st.session_state.etapes_ok = etapes_ok
                st.success(f"AG archivée ✅")
                st.balloons()
                st.rerun()
            except Exception as e: st.error(f"Erreur : {e}")
    if fic or st.session_state.historique_fichier_actuel:
        st.divider()
        st.subheader("🎉 AG complète !")
        nb_ok = len(etapes_ok)
        st.progress(nb_ok/7, text=f"{nb_ok}/7 étapes complétées")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("🏠 Retour au Dashboard", type="primary", use_container_width=True): _nav("dashboard")
        with c2:
            if st.button("➕ Nouvelle AG", use_container_width=True): _nav("nouvelle_ag")
    _nav_btns(etape, etapes_ok)

# ══════════════════════════════════════════════════════════════════════════════
# ROUTER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
mode, api_key, hf_token_ui = _sidebar()

if st.session_state.vue == "dashboard":
    _dashboard()
elif st.session_state.vue == "nouvelle_ag":
    _nouvelle_ag()
elif st.session_state.vue == "workflow":
    _workflow(mode, api_key, hf_token_ui)
else:
    _nav("dashboard")
