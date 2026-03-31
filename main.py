"""
Orchestrateur Principal de la Veille BIM & IA.
Relie le Scraper (Fetcher), l'IA (Analyzer) et la Base de Données locale.
"""
import asyncio
import json
import urllib.parse
from pathlib import Path
from datetime import date, timedelta # AJOUT: timedelta pour calculer les dates de rétention
from loguru import logger

from core.logger import setup_logger
from services.fetcher import BIMFetcher
from services.analyzer import BIMAnalyzer

# Définition du chemin de nos bases de données locales
DB_FILE = Path("data/articles_db.json")
EMBEDDINGS_FILE = Path("data/embeddings_db.json")

# 🎯 LE CŒUR DE LA VEILLE AUTONOME (Élargi pour l'IA Pure)
MOTS_CLES_STRATEGIQUES = [
    # --- Veille BIM & Construction ---
    "Jumeau Numérique BIM",
    "OpenBIM IFC4",
    "Intelligence Artificielle Construction",
    "Revit",
    "pyrevit",
    "IFC"
    
    # --- Veille IA & Dev Pure (NOUVEAU) ---
    "Large Language Models Open Source",
    "Agentic AI Frameworks",
    "Python Data Engineering"
]

async def run_pipeline():
    logger.info("🚀 Démarrage du Pipeline de Veille Agentique...")
    
    fetcher = BIMFetcher()
    analyzer = BIMAnalyzer()
    
    # --- INJECTION DYNAMIQUE DES RADARS GOOGLE NEWS ---
    for mot in MOTS_CLES_STRATEGIQUES:
        url_safe_mot = urllib.parse.quote(mot)
        radar_url = f"https://news.google.com/rss/search?q={url_safe_mot}&hl=fr&gl=FR&ceid=FR:fr"
        source_name = f"Google News 🕵️ ({mot})"
        fetcher.rss_sources[source_name] = radar_url
        logger.debug(f"📡 Radar déployé : '{source_name}'")
    
    existing_articles = []
    seen_urls = set()
    
    if DB_FILE.exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                existing_articles = json.load(f)
                seen_urls = {art["url"] for art in existing_articles}
                logger.info(f"📂 Base de données chargée : {len(existing_articles)} articles connus.")
            except json.JSONDecodeError:
                logger.warning("⚠️ Fichier DB corrompu ou vide. Création d'une nouvelle base.")

    raw_articles = await fetcher.fetch_all()
    
    new_articles = [art for art in raw_articles if art.url not in seen_urls]
    logger.info(f"🔍 {len(new_articles)} NOUVEAUX articles détectés sur {len(raw_articles)} trouvés.")
    
    if not new_articles:
        logger.info("😴 Aucun nouvel article à traiter. Fin du programme.")
        return

    # 🚀 CORRECTION MAJEURE : On ouvre les vannes !
    # Groq permet environ 30 requêtes par minute en version gratuite.
    # On passe la limite de 10 à 30 pour avoir un vrai panel d'articles chaque jour.
    MAX_TO_PROCESS = 30
    articles_to_process = new_articles[:MAX_TO_PROCESS]
    
    processed_articles = []
    logger.info(f"🧠 Envoi de {len(articles_to_process)} articles à l'IA hybride...")
    
    for art in articles_to_process:
        logger.debug(f"Traitement IA : {art.title[:40]}...")
        enriched_article = await analyzer.process_article(art.model_dump())
        enriched_article["date_added"] = date.today().isoformat()
        processed_articles.append(enriched_article)
        
        # On garde 1.5 seconde de pause, ce qui fera un traitement total de ~45 secondes. Très raisonnable.
        await asyncio.sleep(1.5) 
        
    all_articles = existing_articles + processed_articles
    
    # --- 🧹 SÉPARATION ET POLITIQUE DE RÉTENTION (DATA PRUNING) ---
    clean_articles = []
    embeddings_dict = {}
    
    MAX_RETENTION_DAYS = 60 # On garde l'historique de 2 mois
    cutoff_date = date.today() - timedelta(days=MAX_RETENTION_DAYS)
    
    # On charge les favoris pour s'assurer de ne jamais les supprimer
    fav_file = Path("data/favorites.json")
    favorites = set()
    if fav_file.exists():
        with open(fav_file, "r", encoding="utf-8") as f:
            favorites = set(json.load(f))
            
    articles_kept = 0
    articles_pruned = 0
    
    for art in all_articles:
        # Vérification de l'âge de l'article
        art_date_str = art.get("date_added", date.today().isoformat())
        try:
            art_date = date.fromisoformat(art_date_str)
        except ValueError:
            art_date = date.today()
            
        is_favorite = art["url"] in favorites
        is_recent = art_date >= cutoff_date
        
        # Le Gardien : On garde si c'est récent OU si c'est un favori
        if is_recent or is_favorite:
            art_copy = art.copy()
            if "embedding" in art_copy:
                embeddings_dict[art_copy["url"]] = art_copy.pop("embedding")
            clean_articles.append(art_copy)
            articles_kept += 1
        else:
            articles_pruned += 1
            
    if articles_pruned > 0:
        logger.info(f"🧹 Nettoyage : {articles_pruned} anciens articles purgés (Rétention: {MAX_RETENTION_DAYS}j).")
    
    DB_FILE.parent.mkdir(exist_ok=True)
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_articles, f, indent=4, ensure_ascii=False)
        
    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(embeddings_dict, f, ensure_ascii=False)
        
    logger.success(f"💾 {len(processed_articles)} nouveaux articles sauvegardés proprement.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())