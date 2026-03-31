"""Configuration Loguru"""
"""
Configuration centralisée du système de journalisation (logs) avec Loguru.
Remplace le module 'logging' standard de Python pour plus de lisibilité.
"""
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
from loguru import logger  # noqa: E402

def setup_logger():
    """
    Configure Loguru pour écrire dans la console (avec couleurs) 
    et dans un fichier tournant (pour garder une trace historique).
    """
    # 1. On supprime la configuration par défaut de Loguru pour avoir le contrôle total
    logger.remove()
    
    # 2. Ajout du log dans la console (Standard Output)
    # Format clair : Temps | Niveau | Fichier:Ligne | Message
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" # Affiche INFO, WARNING, ERROR, CRITICAL (Ignore DEBUG en production)
    )
    
    # 3. Ajout du log dans un fichier (Mémoire persistante)
    # Très utile pour voir ce que ton script a fait pendant la nuit (CRON)
    log_path = Path("data/app.log")
    
    logger.add(
        str(log_path),
        rotation="10 MB",      # Crée un nouveau fichier quand celui-ci atteint 10 Mo
        retention="1 month",   # Garde l'historique pendant 1 mois, puis supprime les vieux
        level="DEBUG",         # Dans le fichier, on veut TOUT savoir, même les détails techniques
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}"
    )
    
    logger.info("🔧 Système de logs initialisé avec succès.")

# Exécuter la configuration à l'importation de ce module
setup_logger()