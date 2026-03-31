"""Chargement sécurisé du .env avec Pydantic"""
"""
Module de configuration centralisée.
Utilise Pydantic pour valider l'existence et le format des variables d'environnement.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict  # noqa: E402
from pydantic import Field  # noqa: E402

class Settings(BaseSettings):
    """
    Classe définissant les paramètres de l'application.
    Pydantic va automatiquement chercher ces variables dans l'environnement 
    ou dans le fichier .env spécifié.
    """
    # On exige que les clés API soient présentes. 
    # Si elles sont absentes ou vides, l'application crashera proprement au démarrage 
    # au lieu de planter silencieusement au milieu d'une requête réseau.
    groq_api_key: str = Field(..., description="Clé API pour le LLM Cloud (Groq)")
    huggingface_api_key: str = Field(default="", description="Clé API HF (Optionnelle pour l'instant)")
    
    # Configuration du comportement de la veille
    max_articles_per_run: int = Field(default=10, description="Nombre max d'articles à traiter par cycle")
    
    # Indique à Pydantic de lire le fichier .env situé à la racine du projet
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# On instancie la configuration une seule fois (Singleton pattern implicite)
# Partout ailleurs dans le code, on fera : `from core.config import settings`
settings = Settings()