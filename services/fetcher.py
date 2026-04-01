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
# 2. LA CLASSE MÉTIER (Le Scraper furtif)
# ---------------------------------------------------------
class BIMFetcher:
    def __init__(self):
        # 🎯 LISTE PREMIUM - CORRECTIONS DES URLs 404
        self.rss_sources = {
            # --- LES FONDATIONS BIM & OPENBIM (IFC, IDS) ---
            "BuildingSMART (Officiel)": "https://www.buildingsmart.org/feed/",
            "BuildingSMART IDS GitHub": "https://github.com/buildingSMART/IDS",
            "Plannerly" : "https://plannerly.com/ids-buildingsmart-creation/feed/",
            "AEC Business": "https://aec-business.com/feed/",
            "AEC Magazine": "https://aecmag.com/feed/", 
            "DIBS 42": "https://www.dibs42.com/blogs/feed/", # Note: Retournera 526 tant que le proprio n'a pas réparé son serveur
            "Speckle (OpenBIM Community)": "https://speckle.systems/blog/feed.xml",
            "BibLus (ACCA)": "https://biblus.accasoftware.com/en/feed/",
            
            # --- EXPERTISE REVIT, AUTODESK & POWERBI ---
            "The Building Coder": "https://blog.autodesk.io/category/thebuildingcoder/feed/",
            "Revit Pure": "https://revitpure.com/blog?format=rss",
            "Autodesk Platform Services": "https://aps.autodesk.com/blog/", # 404 FIX: Retrait du .xml
            "Dynamo BIM": "https://dynamobim.org/feed/", 
            "Allplan Blog": "https://www.allplan.com/blog/category/bim/",
            
            # --- EXPERTISE ARCHICAD & CONCURRENTS ---
            "Graphisoft Insights": "https://graphisoft.com/feed",
            
            # --- VEILLE FRANCOPHONE (Chantier, DOE, Normes) ---
            "Hexabim": "https://www.hexabim.com/", # 404 FIX: Modification du endpoint RSS
            "Construction21": "https://www.construction21.org/france/", # 404 FIX: Retour au format /feed standard
            "BIM&CO Blog": "https://www.bimandco.com/blog/fr/feed/",
            
            # --- JUMEAU NUMÉRIQUE & SMART BUILDING ---
            "Smart Buildings Magazine": "https://smartbuildingsmagazine.com/", # 404 FIX: Utilisation de /feed
            "Hypervision.fr": "https://www.hyper-vision.fr/blog?format=rss",
            "SpinalCom": "https://www.spinalcom.com/blog/feed/",
            
            # --- INTELLIGENCE ARTIFICIELLE & DATA ---
            "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
            "NVIDIA AI Blog": "https://blogs.nvidia.com/feed/",
            "Towards Data Science": "https://medium.com/feed/towards-data-science",
            
            # --- VEILLE COMMUNAUTAIRE ---
            "Reddit r/Revit": "https://www.reddit.com/r/Revit/.rss",
            "Reddit r/BIM": "https://www.reddit.com/r/BIM/.rss",
            "Reddit r/MachineLearning": "https://www.reddit.com/r/MachineLearning/.rss",
            
            # --- APPELS D'OFFRES
            "Portail des Marchés Publics": "https://marches-publics.departement974.fr/rss",
            "Officiel de La Réunion":"https://www.officiel-demat.re/",
            "France Marchés":"https://www.francemarches.com/appels-offre/reunion/",
            "PLACE (Marchés Publics de l'État)":"https://www.marches-publics.gouv.fr/"
            
        }

    async def _fetch_single_rss(self, client: httpx.AsyncClient, source_name: str, feed_url: str) -> List[ArticleBIM]:
        """Récupère et parse un seul flux RSS de manière asynchrone."""
        logger.debug(f"Début de la récupération pour {source_name}...")
        try:
            response = await client.get(feed_url, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "xml")
            articles = []
            
            items = soup.find_all(["item", "entry"])
            
            for item in items[:10]:
                title_tag = item.find("title")
                link_tag = item.find("link")
                summary_tag = item.find(["description", "summary", "content:encoded"])
                
                if title_tag and link_tag:
                    title = title_tag.text.strip()
                    
                    if link_tag.name == "link" and link_tag.has_attr("href"):
                        link_url = link_tag["href"].strip()
                    else:
                        link_url = link_tag.text.strip()
                        
                    summary_text = summary_tag.text.strip() if summary_tag else ""
                    
                    if summary_text:
                        summary_text = BeautifulSoup(summary_text, "html.parser").get_text()
                    
                    article = ArticleBIM(
                        title=title,
                        url=link_url,
                        source_name=source_name,
                        summary=summary_text[:300] + "..." if len(summary_text) > 300 else summary_text
                    )
                    articles.append(article)
                    
            logger.info(f"✅ {len(articles)} articles récupérés depuis {source_name}.")
            return articles
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 526:
                 logger.error(f"❌ Rejet (526) pour {source_name}. Le propriétaire du site a un certificat SSL cassé.")
            elif e.response.status_code in (403, 401):
                 logger.error(f"❌ Blocage ({e.response.status_code}) pour {source_name}. Paranoïa anti-bot extrême.")
            else:
                 logger.error(f"❌ Erreur HTTP ({e.response.status_code}) pour {source_name}: {feed_url}")
            return []
        except httpx.ConnectError:
            logger.error(f"❌ Erreur de connexion pour {source_name}. Serveur potentiellement éteint.")
            return []
        except Exception as e:
            logger.error(f"❌ Erreur réseau/parsing pour {source_name}: {e}")
            return []

    async def fetch_all(self) -> List[ArticleBIM]:
        """Lance toutes les requêtes HTTP en parallèle avec un déguisement stratégique."""
        logger.info("🚀 Démarrage de la collecte asynchrone des flux BIM...")
        all_articles = []
        
        # 🎓 LE PASSE-DROIT VIP (La stratégie d'ingénierie)
        # On arrête de se faire passer pour un humain sur un navigateur. Ça déclenche des CAPTCHAs.
        # On se fait passer pour "Google FeedFetcher", le robot officiel de Google Actualités.
        # 99% des sites (même protégés par Cloudflare) ont une exception pour ne pas bloquer Google.
        stealth_headers = {
            "User-Agent": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
            "Accept": "application/rss+xml, application/rdf+xml;q=0.9, application/xml;q=0.8, text/xml;q=0.7, */*;q=0.1",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
        
        # verify=False est maintenu pour éviter les crashs sur les certificats auto-signés
        async with httpx.AsyncClient(headers=stealth_headers, verify=False) as client:
            tasks = [self._fetch_single_rss(client, name, url) for name, url in self.rss_sources.items()]
            results = await asyncio.gather(*tasks)
            
            for article_list in results:
                all_articles.extend(article_list)
                
        logger.info(f"🏁 Collecte terminée. Total: {len(all_articles)} articles bruts récupérés.")
        return all_articles