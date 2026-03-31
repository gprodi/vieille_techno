"""
Interface Utilisateur Streamlit pour la Veille BIM & IA.
Architecture dynamique, Recherche Hybride, et Rapports On-Demand avec Sauvegarde.
"""
import json
import urllib.parse # NOUVEAU : Indispensable pour nettoyer proprement l'URL de l'e-mail
from pathlib import Path
from datetime import date
import subprocess
import sys
import streamlit as st
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
from groq import Groq
from core.config import settings

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# ---------------------------------------------------------
st.set_page_config(
    page_title="Veille BIM & IA",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# UTILITAIRE : NETTOYEUR DE CATÉGORIES
# ---------------------------------------------------------
def clean_category(raw_cat):
    """Force les réponses du LLM dans 4 catégories strictes."""
    cat_upper = str(raw_cat).upper()
    if "BIM PUR" in cat_upper: 
        return "BIM Pur 🏗️"
    if "DEV" in cat_upper or "IA" in cat_upper or "INTELLIGENCE" in cat_upper: 
        return "Dev & IA 💻"
    if "HYBRID" in cat_upper: 
        return "Hybride ⚙️"
    return "Veille Globale 🌐"

# ---------------------------------------------------------
# 2. GESTION DU CACHE ET DE L'ÉTAT
# ---------------------------------------------------------
@st.cache_data
def load_data():
    db_path = Path("data/articles_db.json")
    emb_path = Path("data/embeddings_db.json")
    
    if not db_path.exists():
        return []
        
    with open(db_path, "r", encoding="utf-8") as f:
        articles = json.load(f)
        
    if emb_path.exists():
        with open(emb_path, "r", encoding="utf-8") as f:
            embeddings = json.load(f)
            for art in articles:
                if art["url"] in embeddings:
                    art["embedding"] = embeddings[art["url"]]
                    
    today_str = date.today().isoformat()
    for art in articles:
        if "date_added" not in art:
            art["date_added"] = today_str
        art["ai_category_clean"] = clean_category(art.get("ai_category", ""))
            
    return articles

def load_favorites():
    fav_path = Path("data/favorites.json")
    if fav_path.exists():
        with open(fav_path, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_favorites(favorites_set):
    with open("data/favorites.json", "w", encoding="utf-8") as f:
        json.dump(list(favorites_set), f)

@st.cache_resource
def load_local_ai():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer("all-MiniLM-L6-v2", device=device)

# ---------------------------------------------------------
# 3. MOTEUR DE RECHERCHE HYBRIDE
# ---------------------------------------------------------
def hybrid_search(query: str, articles: list, encoder: SentenceTransformer, threshold: float = 0.20):
    if not query or not articles:
        return articles

    query_lower = query.lower()
    query_vector = encoder.encode(query, convert_to_tensor=True)
    results = []
    
    for art in articles:
        text_match = query_lower in art['title'].lower() or query_lower in art.get('ai_summary', '').lower()
        
        semantic_match = False
        similarity = 0.0
        if "embedding" in art:
            art_vector = torch.tensor(art["embedding"], device=query_vector.device)
            similarity = F.cosine_similarity(query_vector.unsqueeze(0), art_vector.unsqueeze(0)).item()
            if similarity >= threshold:
                semantic_match = True
        
        if text_match or semantic_match:
            art_match = dict(art)
            art_match["similarity"] = similarity if "embedding" in art else 0.0
            art_match["match_type"] = "Texte Exact 🎯" if text_match else "Sémantique 🧠"
            results.append(art_match)
            
    return sorted(results, key=lambda x: x["similarity"], reverse=True)

# ---------------------------------------------------------
# 4. CONSTRUCTION DE L'INTERFACE UTILISATEUR
# ---------------------------------------------------------
def main():
    st.title("🏗️ Tour de Contrôle : Veille BIM & IA")
    st.markdown("Interface 100% Autonome avec Recherche Hybride et Rapports à la demande.")
    
    if "favorites" not in st.session_state:
        st.session_state.favorites = load_favorites()
        
    articles = load_data()
    encoder = load_local_ai()
    
    # =========================================================================
    # LE MENU LATÉRAL
    # =========================================================================
    with st.sidebar:
        st.header("🎛️ Filtres Intelligents")
        
        min_score = st.slider(
            "⭐ Score d'intérêt minimum", 
            min_value=0, max_value=10, value=5
        )
        
        st.markdown("---")
        st.subheader("🔎 Recherche Hybride")
        search_query = st.text_input(
            "Chercher un mot ou un concept...",
            placeholder="ex: BIM, Rénovation, IFC..."
        )
        
        st.caption("💡 Cherche instantanément parmi **tous les anciens articles** stockés, en croisant le texte et le sens mathématique (IA vectorielle).")
        
        st.markdown("---")
       
        st.subheader("🚀 Scanner un nouveau thème")
        st.markdown("Un besoin urgent ou un premier démarrage ? Lance les radars.")
        theme_manuel = st.text_input("Thème (ex: Robotique Boston Dynamics)", placeholder="Scanner le web...")

        if st.button("Lancer l'Orchestrateur ⚙️"):
            if theme_manuel:
                with st.spinner(f"Scraping et Analyse Llama-3.1 en cours pour '{theme_manuel}' (≈ 30 à 60 sec)..."):
                    try:
                        subprocess.run([sys.executable, "main.py", "--theme", theme_manuel], check=True)
                        st.success(f"✅ Veille sur '{theme_manuel}' terminée et mails envoyés !")
                        st.cache_data.clear()
                        st.rerun()
                    except subprocess.CalledProcessError as e:
                        st.error("❌ Échec de la recherche : L'orchestrateur a renvoyé une erreur.")
            else:
                st.warning("Veuillez d'abord taper un thème.")

        st.markdown("---")
        st.metric("Total des articles en base", len(articles))

    if not articles:
        st.warning("⚠️ La base de données est vide. Utilise le menu de gauche pour lancer ton premier scan !")
        st.stop() 

    # --- FONCTION DE RENDU D'UNE CARTE ---
    # 🎓 MODIFIÉ : Ajout du paramètre 'force_open' pour le Deep Link
    def render_article_card(art, context_id="", force_open=False):
        score = art.get('ai_score', 0)
        score_color = "🟢" if score >= 8 else ("🟡" if score >= 5 else "🔴")
        is_fav = art['url'] in st.session_state.favorites
        
        fav_icon = "⭐ Retirer favori" if is_fav else "☆ Ajouter favori"
        cat = art.get("ai_category_clean", "Veille Globale 🌐")
        
        display_title = art.get("ai_french_title", art["title"])
        
        btn_fav_key = f"fav_{context_id}_{art['url']}"
        btn_deep_key = f"deep_{context_id}_{art['url']}"
        dl_key = f"dl_{context_id}_{art['url']}"
        report_state_key = f"report_{art['url']}"
        
        with st.expander(f"[{score}/10] {score_color} {display_title} ({art['source_name']})", expanded=force_open):
            col1, col2 = st.columns([5, 1])
            with col1:
                if "match_type" in art:
                    st.caption(f"🎯 Trouvé par : {art['match_type']} (Pertinence: {art['similarity']:.2%})")
                    
                st.markdown(f"**Catégorie IA :** {cat}")
                
                if "ai_french_title" in art and art["ai_french_title"] != art["title"]:
                    st.caption(f"Titre original : *{art['title']}*")
                    
                st.markdown(f"**Résumé :** {art.get('ai_summary', 'Non disponible')}")
                tags = art.get('ai_tags', [])
                if tags:
                    st.markdown("**Mots-clés :** " + " • ".join([f"`{tag}`" for tag in tags]))
                st.markdown(f"[Lire l'article complet]({art['url']})")
                
                # --- GESTION DU RAPPORT DÉTAILLÉ ---
                if report_state_key in st.session_state:
                    st.markdown("---")
                    st.markdown("### 📑 Rapport Détaillé")
                    st.markdown(st.session_state[report_state_key])
                    
                    safe_title = "".join([c for c in display_title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    st.download_button(
                        label="📥 Télécharger le rapport (.md)",
                        data=st.session_state[report_state_key],
                        file_name=f"Rapport_BIM_{safe_title[:30]}.md",
                        mime="text/markdown",
                        key=dl_key
                    )
                else:
                    if st.button("🧠 Générer un rapport détaillé", key=btn_deep_key):
                        with st.spinner("Llama-3.1 rédige le rapport détaillé (environ 5-10 sec)..."):
                            try:
                                client = Groq(api_key=settings.groq_api_key)
                                prompt = f"""
                                Tu es un expert analyste. Rédige une synthèse détaillée (temps de lecture estimé : 4 minutes) 
                                de cet article en FRANÇAIS.
                                Titre : {display_title}
                                Texte brut : {art.get('ai_summary', '')}
                                
                                Instructions de formatage :
                                - Utilise le format Markdown.
                                - Surligne/mets en gras les termes techniques très importants.
                                - Structure en 3 parties : 1. Le Contexte, 2. L'Innovation clé, 3. L'Impact sur l'industrie.
                                """
                                response = client.chat.completions.create(
                                    messages=[{"role": "user", "content": prompt}],
                                    model="llama-3.1-8b-instant",
                                    temperature=0.3
                                )
                                st.session_state[report_state_key] = response.choices[0].message.content
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la communication avec l'IA : {e}")

            with col2:
                if st.button(fav_icon, key=btn_fav_key):
                    if is_fav:
                        st.session_state.favorites.remove(art['url'])
                    else:
                        st.session_state.favorites.add(art['url'])
                    save_favorites(st.session_state.favorites)
                    st.rerun()

    # =========================================================================
    # 🎓 LA SECTION VIP (Gestion du Deep Link par e-mail)
    # Placée tout en haut, avant même les onglets !
    # =========================================================================
    query_params = st.query_params
    deep_link_url = query_params.get("article_url", None)
    
    if deep_link_url:
        # On décode l'URL proprement pour corriger les + et %2F générés par l'e-mail
        decoded_url = urllib.parse.unquote_plus(deep_link_url)
        
        # On cherche l'article dans la base (On teste la version encodée ET décodée)
        target_article = next((a for a in articles if a['url'] == deep_link_url or a['url'] == decoded_url), None)
        
        if target_article:
            st.success("📩 Vous venez depuis un e-mail ! Voici l'article que vous avez demandé :")
            st.markdown("### 🎯 Article à la loupe")
            # force_open=True permet d'ouvrir l'accordéon directement sans clic
            render_article_card(target_article, context_id="vip_deeplink", force_open=True)
            st.markdown("---")
        else:
            st.error("❌ L'article demandé est introuvable. Il a peut-être été purgé de la base de données car il est trop ancien.")

    # --- APPLICATION DES FILTRES POUR LE RESTE DE LA PAGE ---
    categories_existantes = sorted(list(set(art.get("ai_category_clean", "Veille Globale 🌐") for art in articles)))
    filtered_articles = [art for art in articles if art.get("ai_score", 0) >= min_score]
    
    if search_query:
        filtered_articles = hybrid_search(search_query, filtered_articles, encoder)
        st.success(f"🔍 {len(filtered_articles)} résultats trouvés pour '{search_query}'")

    # --- ORGANISATION TEMPORELLE ET ONGLETS PRINCIPAUX ---
    today_str = date.today().isoformat()
    tab_today, tab_archives, tab_favs = st.tabs(["📅 Aujourd'hui", "🗄️ Archives", "⭐ Favoris"])

    # 1. ONGLET : AUJOURD'HUI
    with tab_today:
        st.subheader("Les trouvailles du jour")
        today_arts = [a for a in filtered_articles if a.get("date_added") == today_str]
        
        if not today_arts:
            st.info("Aucun article analysé aujourd'hui qui correspond à tes filtres.")
        else:
            cat_tabs = st.tabs(categories_existantes)
            for i, cat in enumerate(categories_existantes):
                with cat_tabs[i]:
                    cat_arts = [a for a in today_arts if a.get("ai_category_clean", "Veille Globale 🌐") == cat]
                    if not cat_arts:
                        st.write("Aucun article dans cette catégorie aujourd'hui.")
                    for art in cat_arts:
                        render_article_card(art, context_id=f"today_{i}")

    # 2. ONGLET : ARCHIVES
    with tab_archives:
        st.subheader("Historique des veilles")
        arch_arts = [a for a in filtered_articles if a.get("date_added") != today_str]
        if not arch_arts:
            st.info("Aucune archive disponible.")
        else:
            dates = sorted(list(set(a.get("date_added") for a in arch_arts)), reverse=True)
            for d in dates:
                with st.expander(f"📁 Veille du {d}"):
                    day_arts = [a for a in arch_arts if a.get("date_added") == d]
                    for art in day_arts:
                        render_article_card(art, context_id=f"arch_{d}")

    # 3. ONGLET : FAVORIS
    with tab_favs:
        st.subheader("Tes articles sauvegardés")
        fav_arts = [a for a in articles if a['url'] in st.session_state.favorites]
        if not fav_arts:
            st.info("Tu n'as pas encore de favoris. Clique sur ☆ Ajouter favori pour en ajouter !")
        else:
            for art in fav_arts:
                render_article_card(art, context_id="fav")

if __name__ == "__main__":
    main()