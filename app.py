"""
app.py — Interface Streamlit pour l Assistant AG
5 onglets : Transcription · Analyse · PV · Questions · Historique
"""

import os
import json
import tempfile
from datetime import datetime
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

# Imports optionnels — disponibles en local uniquement
try:
    import faster_whisper  # test de la vraie dependance
    import transcriber
    TRANSCRIPTION_DISPONIBLE = True
except ImportError:
    TRANSCRIPTION_DISPONIBLE = False

load_dotenv()

# ─── Fonction utilitaire mode demo ─────────────────────────────────────────────
def _analyse_simulee(demo: dict) -> dict:
    """Retourne une analyse minimale simulee pour le mode demo strict (sans API)."""
    meta = demo.get("metadata", {})
    nb_presents = meta.get("nb_presents", 0) or 0
    nb_representes = meta.get("nb_representes", 0) or 0
    return {
        "meta": {
            "version": "2.0",
            "genere_par": "AG Assistant — mode demo",
            "niveau_confiance_global": "demo",
            "avertissement": "Donnees de demonstration uniquement.",
        },
        "type_ag": meta.get("type", "autre"),
        "informations_generales": {
            "entite": meta.get("nom", "Entite demo"),
            "date": meta.get("date", "non mentionne dans la transcription"),
            "lieu": meta.get("lieu", "non mentionne dans la transcription"),
            "type_assemblee": "AG ordinaire annuelle",
            "heure_ouverture": "non mentionne dans la transcription",
            "heure_cloture": "non mentionne dans la transcription",
            "president_seance": meta.get("president", meta.get("syndic", "non mentionne dans la transcription")),
            "secretaire": "non mentionne dans la transcription",
            "scrutateurs": [],
        },
        "participants": {
            "presents": [{"nom": f"{nb_presents} membres presents", "qualite": "membre", "voix_ou_parts": None, "observations": ""}],
            "representes": [],
            "absents_excuses": [],
            "total_presents": nb_presents,
            "total_representes": nb_representes,
            "total_votants": nb_presents + nb_representes,
            "total_voix": nb_presents + nb_representes,
            "quorum_requis": "Selon statuts",
            "quorum_calcule": None,
            "quorum_atteint": True,
            "base_legale_quorum": "non mentionne dans la transcription",
            "observations_quorum": "Donnees de demonstration",
        },
        "ordre_du_jour": [],
        "resolutions": [],
        "decisions_finales": [],
        "points_divers": ["[Analyse simulee — mode demo sans cle API]"],
        "conformite_legale": {
            "mentions_obligatoires_pv": {},
            "alertes": [],
            "recommandations": [],
        },
        "observations_juridiques": "Donnees de demonstration uniquement.",
        "diarization": [],
    }


# ─── Configuration page ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Assistant AG",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏛️ Assistant AG")
    st.caption("Transcription et synthese d assemblees generales francaises")
    st.divider()

    mode = st.radio(
        "Mode",
        ["🎭 Demo (sans cle API)", "🔑 Avec ma cle API"],
        index=0,
    )

    api_key = None
    hf_token_ui = None

    if mode == "🔑 Avec ma cle API":
        st.caption("🔐 Vos cles ne sont jamais stockees — utilisees uniquement le temps de votre session.")
        api_key = st.text_input(
            "Cle API Anthropic",
            type="password",
            placeholder="sk-ant-...",
            help="Obtenez votre cle sur console.anthropic.com",
        )
        if not api_key:
            st.warning("Cle API requise pour l analyse et la generation de PV.")
        hf_token_ui = st.text_input(
            "Token HuggingFace (optionnel)",
            type="password",
            placeholder="hf_...",
            help="Requis uniquement pour la diarization (identification des locuteurs). Obtenez-le sur huggingface.co/settings/tokens",
        )
        if hf_token_ui:
            st.success("Token HF present — diarization disponible ✅")
        else:
            st.caption("Sans token HF : transcription sans identification des locuteurs.")

    st.divider()
    st.caption("📂 [Code source](https://github.com/PSMAS30/ag-assistant)")
    st.caption("🛠️ Stack : faster-whisper · Claude · Streamlit")

# ─── Session state ─────────────────────────────────────────────────────────────
for key in ["transcription", "segments", "segments_diarises", "locuteurs", "mapping_locuteurs", "analyse", "pv_texte", "demo_key", "historique_fichier_actuel"]:
    if key not in st.session_state:
        st.session_state[key] = None

# demo_historique_session : liste d AG demo chargees en memoire uniquement (ephemere)
if "demo_historique_session" not in st.session_state:
    st.session_state.demo_historique_session = []

# ─── Onglets ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎙️ Transcription", "📋 Analyse AG", "📄 Proces-verbal",
    "💬 Questions", "🗂️ Historique", "📬 Convocation", "👥 Presence"
])

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — TRANSCRIPTION
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("🎙️ Transcription audio")

    if not TRANSCRIPTION_DISPONIBLE:
        st.warning(
            "⚠️ **Transcription audio non disponible sur cette instance.**\n\n"
            "La transcription locale (faster-whisper) et la diarization (pyannote) "
            "necessitent une installation locale avec GPU/CPU dedie.\n\n"
            "👉 Utilisez le **mode demo** ci-dessous pour tester toutes les fonctionnalites, "
            "ou [installez l app en local](https://github.com/PSMAS30/ag-assistant) "
            "pour traiter vos propres enregistrements."
        )

    # Sur Streamlit Cloud, masquer l option audio (transcription non disponible)
    options_source = ["🎭 Utiliser une AG de demo"] if not TRANSCRIPTION_DISPONIBLE else ["📁 Charger un fichier audio", "🎭 Utiliser une AG de demo"]
    source = st.radio(
        "Source",
        options_source,
        horizontal=True,
    )

    if source == "🎭 Utiliser une AG de demo":
        demos = demo_data.list_demos()
        choix = st.selectbox(
            "Choisir une AG de demo",
            options=[d["key"] for d in demos],
            format_func=lambda k: next(d["label"] for d in demos if d["key"] == k),
        )
        if st.button("Charger cette demo", type="primary"):
            d = demo_data.get_demo(choix)
            st.session_state.transcription = d["transcription"].strip()
            st.session_state.segments = None
            st.session_state.demo_key = choix
            st.session_state.analyse = None
            st.session_state.pv_texte = None
            st.success("AG de demo chargee ✅")

    else:
        if not TRANSCRIPTION_DISPONIBLE:
            st.info("💡 Transcription audio disponible uniquement en installation locale. Utilisez le mode demo a gauche.")
            st.stop()

        fichier = st.file_uploader(
            "Fichier audio",
            type=["mp3", "wav", "m4a", "ogg", "flac"],
            help="Formats supportes : MP3, WAV, M4A, OGG, FLAC",
        )
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            modele = st.select_slider(
                "Precision de transcription",
                options=transcriber.MODELES_DISPONIBLES,
                value=transcriber.MODELE_DEFAUT,
                help="Plus le modele est grand, plus la transcription est precise mais lente.",
            )
        with col_opt2:
            activer_diarization = st.toggle(
                "🗣️ Activer la diarization",
                value=False,
                help="Identifie qui parle et quand. Necessite HF_TOKEN dans .env. Premier lancement : ~800 Mo telecharges.",
            )
            if activer_diarization:
                nb_locuteurs_input = st.number_input(
                    "Nombre de locuteurs (0 = auto)",
                    min_value=0, max_value=20, value=0,
                    help="Laisser a 0 pour detection automatique. Specifier si connu pour de meilleurs resultats.",
                )

        if fichier and st.button("Transcrire", type="primary"):
            suffix = "." + fichier.name.rsplit(".", 1)[-1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(fichier.read())
                tmp_path = tmp.name

            try:
                if activer_diarization:
                    hf_token = hf_token_ui or os.getenv("HF_TOKEN", "")
                    if not hf_token:
                        st.error("Token HuggingFace requis pour la diarization — entrez-le dans la barre laterale.")
                        st.stop()
                    with st.spinner("Transcription + diarization en cours (peut prendre quelques minutes)…"):
                        nb_loc = int(nb_locuteurs_input) if nb_locuteurs_input > 0 else None
                        resultat = transcriber.transcrire_avec_diarization(
                            tmp_path, modele=modele, hf_token=hf_token, nb_locuteurs=nb_loc
                        )
                    st.session_state.transcription = resultat["texte"]
                    st.session_state.segments = resultat.get("segments", [])
                    st.session_state.segments_diarises = resultat.get("segments_diarises", [])
                    st.session_state.locuteurs = resultat.get("locuteurs", [])
                    st.session_state.mapping_locuteurs = {l: l for l in resultat.get("locuteurs", [])}
                    st.session_state.analyse = None
                    st.session_state.pv_texte = None
                    duree = resultat.get("duree_secondes", "?")
                    nb_loc_detectes = len(resultat.get("locuteurs", []))
                    st.success(f"Transcription + diarization terminees ✅ ({duree}s — {nb_loc_detectes} locuteurs detectes)")
                else:
                    with st.spinner("Transcription en cours (modele local, sans cloud)…"):
                        resultat = transcriber.transcrire_audio(tmp_path, modele=modele)
                    st.session_state.transcription = resultat["texte"]
                    st.session_state.segments = resultat.get("segments", [])
                    st.session_state.segments_diarises = None
                    st.session_state.locuteurs = None
                    st.session_state.analyse = None
                    st.session_state.pv_texte = None
                    duree = resultat.get("duree_secondes", "?")
                    st.success(f"Transcription terminee ✅ ({duree}s de contenu)")
            except Exception as e:
                st.error(f"Erreur : {e}")
            finally:
                os.unlink(tmp_path)

    # Affichage transcription
    if st.session_state.transcription:
        st.divider()
        st.subheader("Texte transcrit")
        texte_editable = st.text_area(
            "Vous pouvez corriger le texte avant de lancer l analyse.",
            value=st.session_state.transcription,
            height=300,
        )
        if texte_editable != st.session_state.transcription:
            st.session_state.transcription = texte_editable

        # ── Affichage des segments horodates ──────────────────────────────────
        segments = st.session_state.segments
        if segments:
            with st.expander(f"⏱️ Segments horodates ({len(segments)} segments)", expanded=False):
                st.caption("Chaque segment correspond a un passage de parole detecte par Whisper.")
                cols_header = st.columns([1, 1, 6])
                cols_header[0].markdown("**Debut**")
                cols_header[1].markdown("**Fin**")
                cols_header[2].markdown("**Texte**")
                st.divider()
                for seg in segments:
                    def fmt(s):
                        if s is None:
                            return "—"
                        m, s2 = divmod(int(s), 60)
                        return f"{m:02d}:{s2:02d}"
                    c1, c2, c3 = st.columns([1, 1, 6])
                    c1.code(fmt(seg.get("debut")))
                    c2.code(fmt(seg.get("fin")))
                    c3.write(seg.get("texte", ""))
        elif st.session_state.demo_key:
            st.info("ℹ️ Les segments horodates sont disponibles uniquement apres transcription d un fichier audio reel.")

        # ── Panneau diarization ───────────────────────────────────────────────
        segments_diarises = st.session_state.segments_diarises
        locuteurs = st.session_state.locuteurs
        if segments_diarises and locuteurs:
            st.divider()
            st.subheader("🗣️ Diarization — Identification des locuteurs")

            # Renommage interactif
            with st.expander("✏️ Renommer les locuteurs detectes", expanded=True):
                st.caption("Remplacez les identifiants techniques (SPEAKER_00...) par les vrais noms.")
                mapping = st.session_state.mapping_locuteurs or {l: l for l in locuteurs}
                nouveau_mapping = {}
                cols = st.columns(2)
                for i, locuteur in enumerate(locuteurs):
                    with cols[i % 2]:
                        nouveau_nom = st.text_input(
                            f"Nom pour {locuteur}",
                            value=mapping.get(locuteur, locuteur),
                            key=f"nom_loc_{locuteur}",
                        )
                        nouveau_mapping[locuteur] = nouveau_nom
                if st.button("Appliquer les noms", type="secondary"):
                    st.session_state.mapping_locuteurs = nouveau_mapping
                    # Mettre a jour le texte de transcription avec les noms
                    segments_renommes = transcriber.renommer_locuteurs(segments_diarises, nouveau_mapping)
                    st.session_state.segments_diarises = segments_renommes
                    texte_diarise = transcriber.segments_diarises_vers_texte(segments_renommes)
                    st.session_state.transcription = texte_diarise
                    st.success("Noms appliques ✅ — la transcription a ete mise a jour avec les locuteurs.")
                    st.rerun()

            # Affichage timeline par locuteur
            mapping_actuel = st.session_state.mapping_locuteurs or {l: l for l in locuteurs}
            couleurs = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
            locuteurs_couleurs = {loc: couleurs[i % len(couleurs)] for i, loc in enumerate(locuteurs)}

            with st.expander(f"📜 Transcription par locuteur ({len(segments_diarises)} segments)", expanded=False):
                for seg in segments_diarises:
                    loc_tech = seg.get("locuteur_original", seg.get("locuteur", "?"))
                    loc_affiche = mapping_actuel.get(loc_tech, seg.get("locuteur", "?"))
                    couleur = locuteurs_couleurs.get(loc_tech, "#888888")
                    debut = seg.get("debut", 0)
                    m, s = divmod(int(debut), 60)
                    ts = f"{m:02d}:{s:02d}"
                    st.markdown(
                        f'<div style="border-left: 4px solid {couleur}; padding-left: 10px; margin: 4px 0;">'
                        f'<span style="color:{couleur}; font-weight:bold;">{loc_affiche}</span> '
                        f'<span style="color:#888; font-size:0.85em;">[{ts}]</span><br>'
                        f'{seg.get("texte", "")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — ANALYSE AG
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("📋 Analyse de l assemblée générale")

    if not st.session_state.transcription and not st.session_state.analyse:
        st.info("👈 Commencez par charger ou transcrire une AG dans l onglet Transcription.")
    elif st.session_state.analyse and not st.session_state.transcription:
        # AG chargee depuis l historique — afficher l analyse directement
        st.info("ℹ️ AG chargee depuis l historique — analyse disponible ci-dessous.")
    if st.session_state.transcription or st.session_state.analyse:
        # Bouton Analyser uniquement si une transcription est disponible
        if st.session_state.transcription and st.button("Analyser l AG", type="primary"):
            if mode == "🎭 Demo (sans cle API)" and st.session_state.demo_key:
                d = demo_data.get_demo(st.session_state.demo_key)
                # Priorite : cle saisie > cle .env locale > simulation
                cle_effective = api_key or os.getenv("ANTHROPIC_API_KEY", "")
                with st.spinner("Analyse en cours (mode demo)…"):
                    try:
                        if not cle_effective:
                            raise ValueError("Pas de cle API disponible")
                        st.session_state.analyse = analyzer.analyser_transcription(
                            st.session_state.transcription,
                            api_key=cle_effective,
                        )
                        st.success("Analyse terminee ✅")
                    except Exception:
                        st.warning("Aucune cle API disponible — affichage d une analyse simulee.")
                        st.session_state.analyse = _analyse_simulee(d)
            elif api_key:
                with st.spinner("Analyse par Claude en cours…"):
                    try:
                        st.session_state.analyse = analyzer.analyser_transcription(
                            st.session_state.transcription, api_key
                        )
                        # Sauvegarde automatique dans l historique
                        try:
                            chemin = historique_manager.sauvegarder_ag(st.session_state.analyse)
                            st.session_state.historique_fichier_actuel = chemin
                        except Exception:
                            pass
                        st.success("Analyse terminee ✅ — sauvegardee dans l historique")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            else:
                st.warning("Cle API requise pour lancer l analyse.")

        if st.session_state.analyse:
            a = st.session_state.analyse

            # ── Meta conformite ──────────────────────────────────────────────
            meta = a.get("meta", {})
            if meta.get("avertissement"):
                st.warning(f"⚠️ {meta['avertissement']}")

            # ── Metriques principales ────────────────────────────────────────
            infos = a.get("informations_generales", {})
            p = a.get("participants", {})
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Type d AG", a.get("type_ag", "—").replace("_", " ").capitalize())
            col2.metric("Votants", p.get("total_votants", "—"))
            quorum = p.get("quorum_atteint")
            col3.metric("Quorum", "✅ Atteint" if quorum is True else "❌ Non atteint" if quorum is False else "—")
            col4.metric("Confiance IA", meta.get("niveau_confiance_global", "—").capitalize())

            st.subheader(f"{infos.get('entite', '')} — {infos.get('date', '')}")
            if infos.get("lieu"):
                st.caption(f"📍 {infos['lieu']}  |  👤 President : {infos.get('president_seance', '—')}  |  ✍️ Secretaire : {infos.get('secretaire', '—')}")

            # ── Niveaux de confiance par section ────────────────────────────
            conf_sections = a.get("niveaux_confiance_sections", {})
            if conf_sections and any(isinstance(conf_sections.get(k), (int, float)) for k in ["participants", "votes", "quorum"]):
                with st.expander("📊 Niveau de confiance par section", expanded=True):
                    st.caption("Score 0-100 : clarte des informations extraites de la transcription.")

                    def _couleur_score(score):
                        if score is None: return "gray"
                        if score >= 90: return "green"
                        if score >= 70: return "orange"
                        return "red"

                    def _icone_score(score):
                        if score is None: return "—"
                        if score >= 90: return "✅"
                        if score >= 70: return "⚠️"
                        return "❌"

                    sections = [
                        ("Participants", conf_sections.get("participants")),
                        ("Votes", conf_sections.get("votes")),
                        ("Quorum", conf_sections.get("quorum")),
                        ("Convocation", conf_sections.get("convocation")),
                        ("Ordre du jour", conf_sections.get("ordre_du_jour")),
                    ]
                    cols = st.columns(len(sections))
                    for i, (label, score) in enumerate(sections):
                        if score is not None:
                            icone = _icone_score(score)
                            cols[i].metric(label, f"{icone} {score}%")
                            cols[i].progress(int(score) / 100)

            # ── Ordre du jour ────────────────────────────────────────────────
            odj = a.get("ordre_du_jour", [])
            if odj:
                with st.expander(f"📋 Ordre du jour ({len(odj)} points)"):
                    for pt in odj:
                        icone = "✅" if pt.get("traite") else "⏳"
                        st.write(f"{icone} {pt.get('numero', '')}. {pt.get('intitule', '')}")

            # ── Resolutions ──────────────────────────────────────────────────
            def _fmt_ts(val):
                """Formate un timestamp (secondes float ou string HH:MM) en HH:MM:SS."""
                if val is None:
                    return None
                if isinstance(val, (int, float)):
                    h = int(val // 3600)
                    m = int((val % 3600) // 60)
                    s = int(val % 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return str(val)  # deja formate

            resolutions = a.get("resolutions", [])
            if resolutions:
                st.subheader(f"Resolutions ({len(resolutions)})")
                for r in resolutions:
                    statut = r.get("statut", "")
                    icone = "✅" if statut == "adoptée" else "❌" if statut == "rejetée" else "⚠️"
                    # Source horodatee
                    ts = r.get("timestamps", {})
                    ts_debut = _fmt_ts(ts.get("debut"))
                    ts_fin = _fmt_ts(ts.get("fin"))
                    source_label = f"  ·  ⏱ {ts_debut} → {ts_fin}" if ts_debut and ts_fin else ""
                    with st.expander(f"{icone} Resolution {r.get('numero')} — {r.get('titre', r.get('intitule', ''))}{source_label}"):
                        st.write(r.get("description", ""))

                        # Source audio
                        if ts_debut or ts_fin:
                            st.markdown(
                                f"**Source audio :** `{ts_debut or '?'}` → `{ts_fin or '?'}`",
                            )

                        votes = r.get("votes", {})
                        unite = votes.get("unite", "voix")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Pour", f"{votes.get('pour', '—')} {unite}")
                        c2.metric("Contre", f"{votes.get('contre', '—')} {unite}")
                        c3.metric("Abstentions", f"{votes.get('abstentions', votes.get('abstention', '—'))} {unite}")
                        if r.get("base_legale"):
                            st.caption(f"Base legale : {r['base_legale']}")
                        if r.get("majorite_requise"):
                            st.caption(f"Majorite requise : {r['majorite_requise']}")
                        # Niveau de confiance resolution
                        conf_r = r.get("niveau_confiance", "")
                        if conf_r:
                            st.caption(f"Confiance IA : {conf_r}")
                        incertitudes = r.get("sections_incertaines", [])
                        if incertitudes:
                            st.warning("Sections incertaines : " + " | ".join(incertitudes))

            # ── Conformite legale ────────────────────────────────────────────
            conformite = a.get("conformite_legale", {})
            alertes = conformite.get("alertes", [])
            recommandations = conformite.get("recommandations", [])
            if alertes or recommandations:
                with st.expander("⚖️ Conformite legale"):
                    if alertes:
                        st.error("**Alertes :**")
                        for al in alertes:
                            st.write(f"🔴 {al}")
                    if recommandations:
                        st.info("**Recommandations :**")
                        for rec in recommandations:
                            st.write(f"💡 {rec}")

            # ── Points divers ────────────────────────────────────────────────
            points_divers = a.get("points_divers", a.get("incidents_divers", []))
            if points_divers:
                st.subheader("Questions diverses")
                for pt in points_divers:
                    st.write(f"• {pt}")

            # ── Diarization (si disponible) ──────────────────────────────────
            diarization = a.get("diarization", [])
            if diarization:
                with st.expander(f"🗣️ Intervenants identifies ({len(diarization)})"):
                    for d in diarization:
                        ts = d.get("timestamp", "")
                        loc = d.get("locuteur", "?")
                        resume = d.get("contenu_resume", "")
                        st.write(f"**{ts} — {loc}** : {resume}")

            with st.expander("🔍 JSON brut"):
                st.json(a)

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — PROCES-VERBAL
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("📄 Proces-verbal")

    if not st.session_state.analyse:
        st.info("👈 Lancez l analyse dans l onglet Analyse AG d abord.")
    else:
        if st.button("Generer le PV", type="primary"):
            if api_key:
                with st.spinner("Redaction du PV par Claude…"):
                    try:
                        st.session_state.pv_texte = pv_generator.generer_pv_texte(
                            st.session_state.analyse, api_key
                        )
                        # Audit trail
                        if st.session_state.historique_fichier_actuel:
                            historique_manager.ajouter_action_audit(
                                st.session_state.historique_fichier_actuel,
                                "pv_genere", st.session_state.pv_texte
                            )
                        st.success("PV genere ✅")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
            else:
                with st.spinner("Generation du PV (mode demo)…"):
                    st.session_state.pv_texte = pv_generator.pv_demo(st.session_state.analyse)
                    st.success("PV genere en mode demo ✅")

        if st.session_state.pv_texte:
            pv_editable = st.text_area(
                "Proces-verbal — vous pouvez corriger avant export",
                value=st.session_state.pv_texte,
                height=500,
            )
            if pv_editable != st.session_state.pv_texte:
                st.session_state.pv_texte = pv_editable

            st.divider()
            st.caption("📥 Exporter le proces-verbal")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.download_button(
                    "⬇️ Texte (.txt)",
                    data=st.session_state.pv_texte.encode("utf-8"),
                    file_name="proces_verbal_ag.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

            with col2:
                if st.button("⬇️ PDF", use_container_width=True):
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                            tmp_path = tmp.name
                        pv_generator.exporter_pv_pdf(st.session_state.pv_texte, tmp_path)
                        with open(tmp_path, "rb") as f:
                            pdf_bytes = f.read()
                        st.download_button(
                            "📥 Telecharger le PDF",
                            data=pdf_bytes,
                            file_name="proces_verbal_ag.pdf",
                            mime="application/pdf",
                        )
                    except Exception as e:
                        st.error(f"Erreur PDF : {e}")
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass

            with col3:
                if st.button("⬇️ Word (.docx)", use_container_width=True):
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                            tmp_path = tmp.name
                        word_generator.generer_pv_word(st.session_state.analyse, tmp_path)
                        with open(tmp_path, "rb") as f:
                            docx_bytes = f.read()
                        st.download_button(
                            "📥 Telecharger le Word",
                            data=docx_bytes,
                            file_name="proces_verbal_ag.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    except Exception as e:
                        st.error(f"Erreur Word : {e}")
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("💬 Questions sur l AG")

    if not st.session_state.analyse:
        st.info("👈 Lancez l analyse dans l onglet Analyse AG d abord.")
    elif not api_key:
        st.warning("Une cle API est requise pour poser des questions a Claude.")
    else:
        exemples = [
            "Qui a vote contre les travaux ?",
            "Quel etait le quorum requis et a-t-il ete atteint ?",
            "Quelles resolutions ont ete rejetees ?",
            "Quels montants ont ete votes ?",
            "Y a-t-il des points d attention legaux ?",
        ]
        st.caption("Exemples de questions :")
        cols = st.columns(len(exemples))
        question_exemple = None
        for i, ex in enumerate(exemples):
            if cols[i].button(ex, key=f"ex_{i}"):
                question_exemple = ex

        question = st.text_input(
            "Votre question",
            value=question_exemple or "",
            placeholder="Ex : Qui a vote contre la resolution 3 ?",
        )

        if question and st.button("Poser la question", type="primary"):
            with st.spinner("Claude cherche la reponse…"):
                try:
                    reponse = analyzer.poser_question(
                        st.session_state.transcription,
                        st.session_state.analyse,
                        question,
                        api_key,
                    )
                    st.info(reponse)
                except Exception as e:
                    st.error(f"Erreur : {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — HISTORIQUE
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("🗂️ Historique des assemblees generales")

    dossiers = historique_manager.lister_dossiers()
    nb_total = historique_manager.nb_ag_sauvegardees()

    # ── Bouton demo — toujours visible ───────────────────────────────────────
    with st.expander("🎭 Charger des donnees de demonstration", expanded=nb_total == 0):
        st.caption("Charge 4 AG fictives : 2 x Copropriete Les Acacias (2023+2024), Association Elan Vitry, SAS Innov Tech.")
        st.caption("Permet de tester dossiers, comparaison N/N-1, exports sans cle API.")
        col_demo1, col_demo2 = st.columns(2)
        with col_demo1:
            if st.button("📥 Charger les 4 AG demo (session)", type="secondary", key="btn_demo_hist"):
                # Chargement en memoire uniquement — ephemere, disparait au rechargement
                ag_session_existantes = {
                    (e["analyse"].get("informations_generales", {}).get("entite", ""),
                     e["analyse"].get("informations_generales", {}).get("date", ""))
                    for e in st.session_state.demo_historique_session
                }
                nb_charge = 0
                for entree in historique_demo.DEMO_HISTORIQUE:
                    infos = entree["analyse"].get("informations_generales", {})
                    cle = (infos.get("entite", ""), infos.get("date", ""))
                    if cle not in ag_session_existantes:
                        st.session_state.demo_historique_session.append(entree)
                        nb_charge += 1
                if nb_charge > 0:
                    st.success(f"{nb_charge} AG demo chargees en session ✅ (ephemere — non sauvegardees sur disque)")
                    st.rerun()
                else:
                    st.info("Donnees demo deja chargees dans cette session.")
        with col_demo2:
            if st.session_state.demo_historique_session:
                if st.button("🗑️ Vider la demo session", key="btn_vider_demo"):
                    st.session_state.demo_historique_session = []
                    st.rerun()

    # ── AG demo session (ephemeres) ───────────────────────────────────────────
    demo_session = st.session_state.demo_historique_session
    if demo_session:
        st.caption(f"🎭 Session demo : {len(demo_session)} AG (ephemeres — non sauvegardees)")
        # Grouper par entite
        from collections import defaultdict
        demo_par_entite = defaultdict(list)
        for entree in demo_session:
            entite = entree["analyse"].get("informations_generales", {}).get("entite", "Inconnu")
            demo_par_entite[entite].append(entree)

        for entite, entrees in demo_par_entite.items():
            type_ag = entrees[0]["analyse"].get("type_ag", "autre").replace("_", " ").upper()
            with st.expander(f"🎭 **{entite}** — {len(entrees)} AG  |  {type_ag}  *(demo session)*", expanded=True):
                for i, entree in enumerate(entrees):
                    infos = entree["analyse"].get("informations_generales", {})
                    date_ag = infos.get("date", "date inconnue")
                    nb_res = len(entree["analyse"].get("resolutions", []))
                    with st.expander(f"AG du {date_ag} — {nb_res} resolution(s)", expanded=False):
                        if st.button("📂 Charger cette AG", key=f"load_demo_{entite}_{i}"):
                            st.session_state.analyse = entree["analyse"]
                            st.session_state.pv_texte = entree.get("pv_texte")
                            st.session_state.transcription = ""
                            st.session_state.historique_fichier_actuel = None
                            st.success(f"AG demo du {date_ag} chargee ✅ — allez dans l onglet Analyse AG")

        st.divider()

    # ── AG reelles (disque) ───────────────────────────────────────────────────
    if nb_total == 0 and not demo_session:
        st.info("Aucune AG sauvegardee. Utilisez le bouton demo ci-dessus ou analysez une AG avec votre cle API.")
    elif nb_total > 0:
        st.caption(f"💾 Historique disque : {nb_total} AG — {len(dossiers)} dossier(s)")

        # ── Vue groupee par dossier ───────────────────────────────────────────
        for dossier in dossiers:
            ag_du_dossier = historique_manager.lister_ag(dossier=dossier["dossier"])
            type_label = ag_du_dossier[0]["type_ag"].replace("_", " ").upper() if ag_du_dossier else ""

            # Expander niveau 1 : le dossier (entite)
            with st.expander(
                f"📁 **{dossier['entite']}** — {dossier['nb_ag']} AG  |  {type_label}",
                expanded=True,
            ):
                for ag in ag_du_dossier:
                    pv_badge = " 📄" if ag["a_pv"] else ""
                    date_ag = ag["date_ag"] or "date inconnue"
                    date_sauv = ag["sauvegarde_le"][:10] if ag["sauvegarde_le"] else "?"

                    # Ligne AG (expander niveau 2)
                    with st.expander(
                        f"AG du {date_ag} — {ag['nb_resolutions']} resolution(s){pv_badge}",
                        expanded=False,
                    ):
                        st.caption(f"Sauvegarde le {date_sauv}  |  Fichier : {ag['nom_fichier']}")

                        # Audit trail
                        audit = ag.get("audit_trail", [])
                        if len(audit) > 1:
                            with st.expander(f"📋 Audit trail ({len(audit)} action(s))", expanded=False):
                                for acte in audit:
                                    ts = acte.get("timestamp", "")[:16].replace("T", " ")
                                    action = acte.get("action", "").replace("_", " ")
                                    details = acte.get("details", "")
                                    st.write(f"• `{ts}` — **{action}**{': ' + details[:80] if details and len(details) < 80 else ''}")

                        # Boutons action
                        btn1, btn2 = st.columns(2)
                        with btn1:
                            if st.button("📂 Charger cette AG", key=f"load_{ag['nom_fichier']}"):
                                try:
                                    entree = historique_manager.charger_ag(ag["fichier"])
                                    st.session_state.analyse = entree["analyse"]
                                    st.session_state.pv_texte = entree.get("pv_texte")
                                    st.session_state.transcription = entree["analyse"].get("transcription_brute", "")
                                    st.session_state.historique_fichier_actuel = ag["fichier"]
                                    st.success(f"AG du {date_ag} chargee ✅ — allez dans l onglet Analyse AG")
                                except Exception as e:
                                    st.error(f"Erreur chargement : {e}")
                        with btn2:
                            if st.button("🗑️ Supprimer", key=f"del_{ag['nom_fichier']}"):
                                if historique_manager.supprimer_ag(ag["fichier"]):
                                    st.success("AG supprimee.")
                                    st.rerun()
                                else:
                                    st.error("Impossible de supprimer.")

    st.divider()

    # ── Export / Import historique ────────────────────────────────────────────
    st.subheader("💾 Sauvegarde de l historique")
    col_exp, col_imp = st.columns(2)

    with col_exp:
        st.caption("Exporter pour sauvegarde ou transfert")
        # Choix export : tout ou un dossier specifique
        options_exp = ["Tous les dossiers"] + [d["entite"] for d in dossiers]
        choix_exp = st.selectbox("Dossier a exporter", options_exp, key="export_dossier_select")
        dossier_exp = None if choix_exp == "Tous les dossiers" else dossiers[options_exp.index(choix_exp) - 1]["dossier"]

        if st.button("📦 Exporter (.zip)", use_container_width=True):
            try:
                zip_bytes = historique_manager.exporter_historique(dossier=dossier_exp)
                if zip_bytes:
                    nom_zip = f"historique_{dossier_exp or 'complet'}_{datetime.now().strftime('%Y%m%d')}.zip"
                    st.download_button(
                        "📥 Telecharger le ZIP",
                        data=zip_bytes,
                        file_name=nom_zip,
                        mime="application/zip",
                    )
                else:
                    st.info("Dossier vide — rien a exporter.")
            except Exception as e:
                st.error(f"Erreur export : {e}")

    with col_imp:
        st.caption("Restaurer un historique precedemment exporte")
        zip_upload = st.file_uploader("Importer un ZIP d historique", type=["zip"], key="import_hist")
        if zip_upload and st.button("📂 Importer", use_container_width=True):
            try:
                nb_import = historique_manager.importer_historique(zip_upload.read())
                st.success(f"{nb_import} AG importee(s) ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur import : {e}")

    st.divider()

    # ── Comparaison N vs N-1 ──────────────────────────────────────────────────
    st.subheader("📊 Comparaison N vs N-1")

    # Construire liste unifiee disque + session demo
    ag_list_comp_disque = historique_manager.lister_ag()
    ag_list_comp_session = [
        {
            "entite": e["analyse"].get("informations_generales", {}).get("entite", "Demo"),
            "date_ag": e["analyse"].get("informations_generales", {}).get("date", ""),
            "fichier": f"__session__{i}",
            "_analyse": e["analyse"],
        }
        for i, e in enumerate(st.session_state.demo_historique_session)
    ]
    ag_list_comp = [
        {**ag, "_source": "disque"} for ag in ag_list_comp_disque
    ] + [
        {**ag, "_source": "session"} for ag in ag_list_comp_session
    ]

    if len(ag_list_comp) < 2:
        st.info("Au moins 2 AG sont necessaires pour effectuer une comparaison (historique disque ou demo session).")
    else:
        options = {
            f"{ag['entite']} — {ag['date_ag'] or ''} {'🎭' if ag['_source']=='session' else '💾'}": ag
            for ag in ag_list_comp
        }
        labels = list(options.keys())

        col_a, col_b = st.columns(2)
        with col_a:
            label_ag1 = st.selectbox("AG N-1 (ancienne)", labels, index=min(1, len(labels)-1), key="comp_ag1")
        with col_b:
            label_ag2 = st.selectbox("AG N (recente)", labels, index=0, key="comp_ag2")

        if st.button("Comparer ces deux AG", type="primary"):
            if label_ag1 == label_ag2:
                st.warning("Selectionnez deux AG differentes.")
            else:
                try:
                    ag1_entry = options[label_ag1]
                    ag2_entry = options[label_ag2]
                    # Utiliser comparer_ag (disque) ou comparer_analyses_dict (session)
                    if ag1_entry["_source"] == "disque" and ag2_entry["_source"] == "disque":
                        rapport = historique_manager.comparer_ag(ag1_entry["fichier"], ag2_entry["fichier"])
                    elif ag1_entry["_source"] == "session" and ag2_entry["_source"] == "session":
                        rapport = historique_manager.comparer_analyses_dict(ag1_entry["_analyse"], ag2_entry["_analyse"])
                    else:
                        # Mix disque + session : charger l analyse disque
                        def _get_analyse(entry):
                            if entry["_source"] == "disque":
                                return historique_manager.charger_ag(entry["fichier"])["analyse"]
                            return entry["_analyse"]
                        rapport = historique_manager.comparer_analyses_dict(_get_analyse(ag1_entry), _get_analyse(ag2_entry))

                    # Entetes
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**AG N-1** : {rapport['ag1']['entite']} — {rapport['ag1']['date']}")
                    c2.markdown(f"**AG N** : {rapport['ag2']['entite']} — {rapport['ag2']['date']}")

                    st.divider()

                    # Quorum
                    st.subheader("Quorum")
                    q = rapport["quorum"]
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Quorum N-1", "✅" if q["ag1_atteint"] else "❌" if q["ag1_atteint"] is False else "—")
                    col2.metric("Quorum N", "✅" if q["ag2_atteint"] else "❌" if q["ag2_atteint"] is False else "—")
                    if q["ag1_calcule"] and q["ag2_calcule"]:
                        delta = q["ag2_calcule"] - q["ag1_calcule"]
                        col3.metric("Voix N-1", q["ag1_calcule"])
                        col4.metric("Voix N", q["ag2_calcule"], delta=f"{delta:+d}")

                    # Participants
                    st.subheader("Participants")
                    p = rapport["participants"]
                    col1, col2 = st.columns(2)
                    col1.metric("Votants N-1", p["ag1_votants"] or "—")
                    col2.metric("Votants N", p["ag2_votants"] or "—")

                    # Resolutions communes
                    res_communes = rapport["resolutions_communes"]
                    if res_communes:
                        st.subheader(f"Resolutions communes ({len(res_communes)})")
                        for r in res_communes:
                            icone = "🔄" if r["statut_change"] else "➡️"
                            with st.expander(f"{icone} {r['titre']}", expanded=r["statut_change"]):
                                col1, col2 = st.columns(2)
                                col1.markdown(f"**N-1** : {r['statut_ag1'] or '—'}")
                                col2.markdown(f"**N** : {r['statut_ag2'] or '—'}")
                                if r["statut_change"]:
                                    st.warning("Statut change entre les deux AG")
                                v1 = r["votes_ag1"]
                                v2 = r["votes_ag2"]
                                if any(v is not None for v in [v1.get("pour"), v2.get("pour")]):
                                    c1, c2, c3 = st.columns(3)
                                    c1.metric("Pour N-1 → N", f"{v1.get('pour', '?')} → {v2.get('pour', '?')}")
                                    c2.metric("Contre N-1 → N", f"{v1.get('contre', '?')} → {v2.get('contre', '?')}")
                                    c3.metric("Abstentions N-1 → N", f"{v1.get('abstentions', '?')} → {v2.get('abstentions', '?')}")

                    # Nouvelles / disparues
                    if rapport["nouvelles_resolutions"]:
                        st.subheader("🆕 Nouvelles resolutions (AG N uniquement)")
                        for t in rapport["nouvelles_resolutions"]:
                            st.write(f"• {t}")

                    if rapport["resolutions_disparues"]:
                        st.subheader("🗑️ Resolutions absentes en N")
                        for t in rapport["resolutions_disparues"]:
                            st.write(f"• {t}")

                except Exception as e:
                    st.error(f"Erreur comparaison : {e}")

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 6 — CONVOCATION
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("📬 Generateur de convocation")
    st.caption("Genere une convocation conforme avec les mentions legales obligatoires selon le type d entite.")

    if not st.session_state.analyse:
        st.info("👈 Chargez ou analysez une AG d abord pour pre-remplir la convocation. Ou remplissez les champs manuellement.")

    col1, col2 = st.columns(2)
    with col1:
        date_conv_input = st.date_input("Date d envoi de la convocation", value=datetime.now())
        date_ag_input = st.text_input("Date proposee de l AG prochaine", placeholder="ex: 15/06/2025")
    with col2:
        lieu_input = st.text_input(
            "Lieu de l AG",
            value=st.session_state.analyse.get("informations_generales", {}).get("lieu", "") if st.session_state.analyse else "",
            placeholder="Adresse ou salle"
        )

    if st.button("Generer la convocation", type="primary"):
        analyse_conv = st.session_state.analyse or {}
        date_conv_str = date_conv_input.strftime("%d/%m/%Y") if date_conv_input else None

        col_pdf, col_word = st.columns(2)
        with col_pdf:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_path = tmp.name
                convocation_generator.generer_convocation_pdf(analyse_conv, tmp_path, date_conv_str, date_ag_input or None, lieu_input or None)
                with open(tmp_path, "rb") as f:
                    st.download_button("📥 Convocation PDF", data=f.read(), file_name="convocation_ag.pdf", mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Erreur PDF : {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except OSError: pass

        with col_word:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                    tmp_path = tmp.name
                convocation_generator.generer_convocation_word(analyse_conv, tmp_path, date_conv_str, date_ag_input or None, lieu_input or None)
                with open(tmp_path, "rb") as f:
                    st.download_button("📥 Convocation Word", data=f.read(), file_name="convocation_ag.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            except Exception as e:
                st.error(f"Erreur Word : {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except OSError: pass

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 7 — FEUILLE DE PRESENCE
# ══════════════════════════════════════════════════════════════════════════════
with tab7:
    st.header("👥 Feuille de presence")
    st.caption("Genere une feuille de presence pre-remplie depuis l analyse AG.")

    if not st.session_state.analyse:
        st.info("👈 Analysez une AG d abord pour pre-remplir la feuille de presence.")
    else:
        analyse_fp = st.session_state.analyse
        infos_fp = analyse_fp.get("informations_generales", {})
        p_fp = analyse_fp.get("participants", {})

        col1, col2, col3 = st.columns(3)
        col1.metric("Presents", p_fp.get("total_presents", "—"))
        col2.metric("Representes", p_fp.get("total_representes", "—"))
        col3.metric("Total votants", p_fp.get("total_votants", "—"))

        if st.button("Generer la feuille de presence", type="primary"):
            col_pdf, col_word = st.columns(2)
            with col_pdf:
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp_path = tmp.name
                    presence_generator.generer_feuille_presence_pdf(analyse_fp, tmp_path)
                    with open(tmp_path, "rb") as f:
                        st.download_button("📥 Presence PDF", data=f.read(), file_name="feuille_presence_ag.pdf", mime="application/pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur PDF : {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try: os.unlink(tmp_path)
                        except OSError: pass

            with col_word:
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                        tmp_path = tmp.name
                    presence_generator.generer_feuille_presence_word(analyse_fp, tmp_path)
                    with open(tmp_path, "rb") as f:
                        st.download_button("📥 Presence Word", data=f.read(), file_name="feuille_presence_ag.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur Word : {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try: os.unlink(tmp_path)
                        except OSError: pass
