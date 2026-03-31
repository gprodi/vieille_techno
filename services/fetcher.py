"""
Moteur de récupération asynchrone pour la veille BIM.
Utilise httpx pour les requêtes non bloquantes et BeautifulSoup pour le parsing.
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

# ---------------------------------------------------------
# 1. MODÈLES DE DONNÉES (Validation Pydantic)
# ---------------------------------------------------------
class ArticleBIM(BaseModel):
    title: str = Field(..., description="Le titre de l'article")
    url: str = Field(..., description="L'URL absolue vers l'article")
    source_name: str = Field(..., description="Le nom du média")
    summary: Optional[str] = Field(default="", description="Description courte ou extrait")

# ---------------------------------------------------------
# 2. LA CLASSE MÉTIER (Le Scraper)
# ---------------------------------------------------------
class BIMFetcher:
    def __init__(self):
        # Liste des sources STATIQUES de haute qualité (BIM, IA, et Développement)
        # Note : L'orchestrateur (main.py) viendra injecter dynamiquement les radars Google News ici.
        self.rss_sources = {
            # --- LES FONDATIONS BIM & OPENBIM (IFC, IDS) ---
            "BuildingSMART (Officiel)": "https://www.buildingsmart.org/feed/", # Pour les standards IFC et IDS
            "AEC Business": "https://aec-business.com/feed/",
            "AEC Magazine": "https://aecmag.com/feed/", 
            "BIM 42": "https://bim42.com/feed/",
            "Speckle (OpenBIM)": "https://speckle.systems/rss/",
            "BibLus (ACCA)": "https://biblus.accasoftware.com/en/feed/",
            
            # --- EXPERTISE REVIT, AUTODESK & POWERBI ---
            "The Building Coder": "https://thebuildingcoder.typepad.com/blog/atom.xml", # LA bible API Revit (pour Mdeboeuf)
            "Revit Pure": "https://revitpure.com/blog?format=rss", # Excellents tutos Revit
            "Autodesk Platform Services": "https://aps.autodesk.com/blog/rss", # Pour les intégrations cloud/PowerBI
            "Dynamo BIM": "https://dynamobim.org/feed/", 
            
            # --- EXPERTISE ARCHICAD & CONCURRENTS ---
            "Graphisoft Insights": "https://graphisoft.com/feed", # Pour ArchiCAD (Crottiers)
            
            # --- VEILLE FRANCOPHONE (Chantier, DOE, Normes) ---
            "Hexabim": "https://www.hexabim.com/feed", # La plus grosse commu FR
            "Construction21": "https://www.construction21.org/france/rss.xml", # Marché FR et smart building
            "BIM&CO Blog": "https://www.bimandco.com/blog/fr/feed/",
            
            # --- JUMEAU NUMÉRIQUE & SMART BUILDING ---
            "Smart Buildings Magazine": "https://smartbuildingsmagazine.com/feed.xml", # Pour l'hypervision (Apassard)
            
            # --- INTELLIGENCE ARTIFICIELLE & DATA ---
            "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
            "NVIDIA AI Blog": "https://blogs.nvidia.com/feed/",
            "Towards Data Science": "https://medium.com/feed/towards-data-science",
            
            # --- VEILLE COMMUNAUTAIRE ---
            "Reddit r/Revit": "https://www.reddit.com/r/Revit/.rss",
            "Reddit r/BIM": "https://www.reddit.com/r/BIM/.rss",
            "Reddit r/MachineLearning": "https://www.reddit.com/r/MachineLearning/.rss"
        }
        
        # En-têtes HTTP avancés (Camouflage "Anti-Bot")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
            "Accept": "application/rss+xml, application/rdf+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
            "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive"
        }

    async def _fetch_single_rss(self, client: httpx.AsyncClient, source_name: str, url: str) -> List[ArticleBIM]:
        logger.debug(f"Début de la récupération pour {source_name}...")
        articles = []
        
        try:
            # follow_redirects=True pour suivre automatiquement les 301 / 302
            response = await client.get(
                url, 
                headers=self.headers, 
                timeout=15.0, 
                follow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "xml")
            
            # Le parseur Bilingue (RSS = "item", Atom = "entry")
            items = soup.find_all(["item", "entry"])
            
            for item in items[:5]:
                # Extraction du Titre
                title_tag = item.find("title")
                title_text = title_tag.text.strip() if title_tag else "Sans Titre"
                
                # Extraction de l'URL
                link_tag = item.find("link")
                link_url = ""
                if link_tag:
                    if link_tag.text.strip():
                        link_url = link_tag.text.strip()
                    elif link_tag.has_attr("href"):
                        link_url = link_tag["href"]
                
                # Extraction de la description
                desc_tag = item.find("description") or item.find("summary") or item.find("content")
                summary_text = desc_tag.text.strip() if desc_tag else ""
                
                # Validation Pydantic
                if title_text and link_url:
                    article = ArticleBIM(
                        title=title_text,
                        url=link_url,
                        source_name=source_name,
                        summary=summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
                    )
                    articles.append(article)
                    
            logger.info(f"✅ {len(articles)} articles récupérés depuis {source_name}.")
            return articles
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Rejet serveur ({e.response.status_code}) pour {source_name}. Le flux n'existe plus ou bloque les bots.")
            return []
        except httpx.RequestError as e:
            logger.error(f"❌ Erreur réseau pour {source_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur de parsing pour {source_name}: {e}")
            return []

    async def fetch_all(self) -> List[ArticleBIM]:
        logger.info("🚀 Démarrage de la collecte asynchrone des flux BIM...")
        all_articles = []
        
        async with httpx.AsyncClient() as client:
            tasks = [self._fetch_single_rss(client, name, url) for name, url in self.rss_sources.items()]
            results = await asyncio.gather(*tasks)
            
            for article_list in results:
                all_articles.extend(article_list)
                
        logger.info(f"🏁 Collecte terminée. Total: {len(all_articles)} articles récupérés.")
        return all_articles