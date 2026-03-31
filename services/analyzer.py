"""
Moteur d'Intelligence Artificielle Hybride.
- Analyse Sémantique (Cloud) : Groq (Llama-3.1)
- Vectorisation (Local) : PyTorch (CPU/CUDA)
"""
import json
import asyncio
import torch
from groq import AsyncGroq
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from loguru import logger

# --- ASTUCE DE SENIOR (PYTHONPATH) ---
# Indispensable pour que Python trouve le module 'core' lorsqu'il est lancé
# depuis différents endroits du projet.
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
# -------------------------------------

from core.config import settings

# ---------------------------------------------------------
# 1. MODÈLES DE DONNÉES (Pour structurer la sortie de l'IA)
# ---------------------------------------------------------
class AIAnalysisResult(BaseModel):
    """Ce modèle définit exactement ce qu'on attend du LLM (Garde-fou)."""
    french_title: str = Field(..., description="Le titre de l'article traduit en français")
    score: int = Field(..., description="Note d'intérêt de l'article de 1 à 10 pour un professionnel du BIM")
    summary: str = Field(..., description="Résumé très détaillé en français (minimum 3 à 4 phrases complètes, soit environ 3 lignes denses).")
    tags: List[str] = Field(..., description="3 à 5 mots-clés spécifiques (ex: Revit, API, LLM, Jumeau Numérique)")
    category: str = Field(..., description="Catégorie stricte parmi : 'BIM Pur 🏗️', 'Dev & IA 💻', 'Hybride ⚙️', 'Veille Globale 🌐'")

# ---------------------------------------------------------
# 2. LA CLASSE MÉTIER (L'Analyseur)
# ---------------------------------------------------------
class BIMAnalyzer:
    def __init__(self):
        # 1. Initialisation du client Cloud (Groq)
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        
        # 2. Détection du Matériel (La magie de PyTorch)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️  Matériel IA détecté : {self.device.upper()}")
        if self.device == "cuda":
            logger.info(f"🎮 Carte graphique : {torch.cuda.get_device_name(0)}")
            
        # 3. Chargement du modèle local d'Embedding
        logger.info("🧠 Chargement du modèle d'embedding local...")
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)

    async def _analyze_text_with_llm(self, title: str, summary: str) -> Dict[str, Any]:
        """
        Envoie le titre et le contenu brut à Groq pour obtenir une analyse structurée
        en forçant le mode JSON (JSON Mode).
        """
         # 🎓 NOUVEAU : Le Prompt a été durci pour forcer des résumés longs et argumentés.
        prompt = f"""
        Tu es un Ingénieur Expert en BIM, Architecture et Intelligence Artificielle.
        Voici un article fraîchement récupéré sur le web :
        
        Titre original : {title}
        Texte brut/extrait : {summary}

        TA MISSION :
        1. Donne un 'score' sur 10 (10 = révolution technique majeure, 0 = hors sujet/spam). Sois très critique, donne 7 ou plus uniquement aux articles avec une vraie valeur technique.
        2. Rédige un 'summary' EXHAUSTIF en français. Interdiction formelle de faire une seule phrase. Tu DOIS rédiger un paragraphe consistant de 3 ou 4 phrases bien construites (environ 3 à 4 lignes). Explique le contexte, l'innovation technique, et l'impact potentiel sur le secteur de la construction/BIM.
        3. Traduis le 'french_title' proprement.
        4. Extrais 3 à 5 mots-clés pertinents.
        5. Classe l'article dans UNE SEULE de ces catégories exactes : 'BIM Pur 🏗️', 'Dev & IA 💻', 'Hybride ⚙️' ou 'Veille Globale 🌐'.
        
        RÉPONDS UNIQUEMENT AU FORMAT JSON STRICT avec les clés:"french_title","score", "summary", "tags", "category".
        """
        
        try:
            # Appel à Llama 3.1 8B (Modèle rapide, idéal pour le tri massif)
            response = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"}, 
                temperature=0.2 # Température basse pour éviter les hallucinations
            )
            
            raw_json = response.choices[0].message.content
            parsed_data = json.loads(raw_json)
            
            # Validation rigoureuse via Pydantic
            validated_data = AIAnalysisResult(**parsed_data)
            return validated_data.model_dump()
            
        except Exception as e:
            logger.error(f"❌ Erreur Groq pour l'article '{title[:20]}...': {e}")
            # Mode dégradé : Si l'IA plante, on renvoie une valeur par défaut pour ne pas crasher le script
            return {
                "score": 0, 
                "summary": "Erreur d'analyse IA.", 
                "tags": [], 
                "category": "Veille Globale 🌐"
            }

    def vectorize_local(self, text: str) -> List[float]:
        """
        Génère une signature mathématique du texte (384 dimensions)
        pour permettre la recherche sémantique locale.
        """
        vector = self.encoder.encode(text)
        return vector.tolist()

    async def process_article(self, article: dict) -> dict:
        """
        Chef d'orchestre pour un article : 
        1. Compréhension Cloud (Llama 3.1)
        2. Mathématisation Locale (PyTorch)
        """
        # Phase 1 : Extraction du sens (Cloud)
        ai_data = await self._analyze_text_with_llm(article["title"], article.get("summary", ""))
        
        # Phase 2 : Calcul vectoriel (Local)
        vector = self.vectorize_local(ai_data["summary"])
        
        # Phase 3 : Enrichissement de l'objet
        enriched_article = {
            **article,
            "ai_french_title": ai_data.get("french_title", article["title"]),
            "ai_score": ai_data["score"],
            "ai_summary": ai_data["summary"],
            "ai_tags": ai_data["tags"],
            "ai_category": ai_data["category"],
            "embedding": vector
        }
        return enriched_article