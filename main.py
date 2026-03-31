"""
Orchestrateur Principal de la Veille BIM & IA.
Relie le Scraper (Fetcher), l'IA (Analyzer) et la Base de Données locale.
"""
import asyncio
import json
import urllib.parse
import argparse
import sys
from pathlib import Path
from datetime import date, timedelta
from loguru import logger

from core.logger import setup_logger
from services.fetcher import BIMFetcher
from services.analyzer import BIMAnalyzer
from services.reporter import ReporterService

# Définition du chemin de nos bases de données locales
DB_FILE = Path("data/articles_db.json")
EMBEDDINGS_FILE = Path("data/embeddings_db.json")

# 🎯 LA BASE INCOMPRESSIBLE DE L'AGENCE
MOTS_CLES_STRATEGIQUES_BASE = [
    "BIM",
    "Intelligence Artificielle Construction",
    "Revit"
]

# Durée de conservation des articles dans la base de données
MAX_RETENTION_DAYS = 30

async def run_pipeline(theme_cible: str = None):
    logger.info("🚀 Démarrage du Pipeline de Veille Agentique...")
    
    fetcher = BIMFetcher()
    analyzer = BIMAnalyzer()
    
    # --- INJECTION DYNAMIQUE DES RADARS GOOGLE NEWS ---
    if theme_cible:
        mots_a_chercher = [theme_cible]
    else:
        interets_collegues = ReporterService.get_tous_les_mots_cles()
        mots_a_chercher = list(set(MOTS_CLES_STRATEGIQUES_BASE + interets_collegues))
        logger.info(f"📡 Radars synchronisés avec l'annuaire ! {len(mots_a_chercher)} cibles.")
    
    for mot in mots_a_chercher:
        url_safe_mot = urllib.parse.quote(mot)
        radar_url = f"https://news.google.com/rss/search?q={url_safe_mot}&hl=fr&gl=FR&ceid=FR:fr"
        fetcher.rss_sources[f"Google News 🕵️ ({mot})"] = radar_url

    # --- 1. COLLECTE ---
    all_articles = await fetcher.fetch_all()
    
    # --- 2. DÉDUPLICATION (Basée sur l'URL) ---
    known_urls = set()
    if DB_FILE.exists():
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                existing_articles = json.load(f)
                known_urls = {art["url"] for art in existing_articles}
                all_articles.extend(existing_articles)
            logger.info(f"📂 Base de données chargée : {len(known_urls)} articles connus.")
        except json.JSONDecodeError:
            logger.warning("⚠️ Fichier DB corrompu ou vide. Création d'une nouvelle base.")

    # On isole les vrais nouveaux articles
    new_articles_to_process = [art for art in all_articles if art.url not in known_urls]
    
    # Pour la déduplication de la liste complète (anciens + nouveaux non traités)
    unique_articles_dict = {}
    for art in all_articles:
        url = art.url if hasattr(art, 'url') else art.get("url")
        if url not in unique_articles_dict:
            unique_articles_dict[url] = art
            
    all_articles = list(unique_articles_dict.values())
    
    logger.info(f"🔍 {len(new_articles_to_process)} NOUVEAUX articles détectés sur {len(all_articles)} trouvés.")

    # --- 3. TRAITEMENT IA (Seulement pour les nouveaux) ---
    processed_articles = []
    if new_articles_to_process:
        logger.info(f"🧠 Envoi de {len(new_articles_to_process)} articles à l'IA hybride...")
        
        for raw_art in new_articles_to_process:
            art_dict = raw_art.model_dump() if hasattr(raw_art, 'model_dump') else raw_art
            enriched_art = await analyzer.process_article(art_dict)
            enriched_art["date_added"] = date.today().isoformat()
            processed_articles.append(enriched_art)

    # Mise à jour de la grande liste avec les articles enrichis
    for enriched_art in processed_articles:
        for i, art in enumerate(all_articles):
            url = art.url if hasattr(art, 'url') else art.get("url")
            if url == enriched_art["url"]:
                all_articles[i] = enriched_art
                break

    # --- 4. NETTOYAGE (PRUNING) ET SÉPARATION DES EMBEDDINGS ---
    cutoff_date = date.today() - timedelta(days=MAX_RETENTION_DAYS)
    clean_articles = []
    embeddings_dict = {}
    
    if EMBEDDINGS_FILE.exists():
        try:
            with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                embeddings_dict = json.load(f)
        except json.JSONDecodeError:
            pass

    articles_pruned = 0
    
    # 🎓 C'est ICI que l'on a retiré la logique des Favoris !
    for art in all_articles:
        # Si c'est un objet Pydantic, on le convertit en dict
        if hasattr(art, 'model_dump'):
            art = art.model_dump()
            
        art_date_str = art.get("date_added", date.today().isoformat())
        try:
            art_date = date.fromisoformat(art_date_str)
        except ValueError:
            art_date = date.today()
            
        is_recent = art_date >= cutoff_date
        
        # Le Gardien simplifié : On garde uniquement si c'est récent
        if is_recent:
            art_copy = art.copy()
            if "embedding" in art_copy:
                embeddings_dict[art_copy["url"]] = art_copy.pop("embedding")
            clean_articles.append(art_copy)
        else:
            articles_pruned += 1
            # Nettoyage de l'embedding associé s'il existait
            if art["url"] in embeddings_dict:
                del embeddings_dict[art["url"]]
            
    if articles_pruned > 0:
        logger.info(f"🧹 Nettoyage : {articles_pruned} anciens articles purgés (Rétention: {MAX_RETENTION_DAYS}j).")
    
    DB_FILE.parent.mkdir(exist_ok=True)
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_articles, f, indent=4, ensure_ascii=False)
        
    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(embeddings_dict, f, ensure_ascii=False)
        
    logger.success("💾 Base mise à jour proprement.")

    # --- 5. DISTRIBUTION DES EMAILS ---
    if processed_articles:
        logger.info("📮 Lancement du ReporterService pour distribuer la veille aux collègues...")
        STREAMLIT_PUBLIC_URL = "https://vieille-techno-ebim.streamlit.app" 
        ReporterService.distribuer_veille(processed_articles, base_url=STREAMLIT_PUBLIC_URL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrateur de Veille")
    parser.add_argument("--theme", type=str, help="Forcer la recherche sur un thème précis", default=None)
    args = parser.parse_args()
    
    asyncio.run(run_pipeline(theme_cible=args.theme))