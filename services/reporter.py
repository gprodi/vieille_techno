"""
Service dédié à la communication externe et aux rapports.
Gère le formatage et l'envoi des newsletters de veille.
"""
from typing import List, Dict
from loguru import logger

class ReporterService:
    """
    Classe utilitaire pour la gestion des rapports et notifications.
    Pourquoi une classe ? Pour pouvoir facilement la faire évoluer plus tard 
    (ex: ajouter une méthode send_to_slack, send_to_teams, etc.)
    """

    @staticmethod
    def generer_corps_email(articles: List[Dict], base_url: str) -> str:
        """
        [NOUVEAU] - Le générateur de newsletter avec Deep Links.
        
        POURQUOI ICI ?
        Séparation des préoccupations. Le composant UI (Streamlit) n'a pas à 
        savoir comment on formate un e-mail en Markdown ou en HTML.
        
        Args:
            articles: Liste des articles filtrés par l'utilisateur.
            base_url: L'URL publique de votre application Streamlit.
        """
        if not articles:
            return "Aucun article sélectionné pour cette veille."

        lignes = []
        lignes.append("## 📡 Votre Veille Technologique BIM & IA\n")
        lignes.append("Bonjour, voici la sélection d'articles qui pourrait vous intéresser :\n")
        
        for art in articles:
            titre = art.get('title', 'Titre inconnu')
            # On récupère le résumé IA ou le résumé court classique
            resume = art.get('ai_summary', art.get('summary', 'Pas de résumé disponible.'))
            url_source = art.get('url', '')
            
            lignes.append(f"### 📌 {titre}")
            lignes.append(f"> {resume}")
            
            # --- LE COEUR DU SYSTÈME : LE DEEP LINK ---
            # On encode l'URL de l'article pour qu'elle passe de manière "safe" dans notre propre URL Streamlit
            import urllib.parse
            safe_url = urllib.parse.quote_plus(url_source)
            lien_vers_app = f"{base_url}/?article_url={safe_url}"
            
            lignes.append(f"👉 **[Lire l'analyse IA complète et détaillée sur l'application]({lien_vers_app})**")
            lignes.append(f"🔗 *[Source originale]({url_source})*")
            lignes.append("\n---\n")
            
        return "\n".join(lignes)

    @staticmethod
    def envoyer_email(destinataires: str, contenu: str):
        """
        [NOUVEAU] - Simulation d'envoi.
        Dans le futur, vous pourrez remplacer ce print par du SMTP (smtplib) 
        ou une API comme SendGrid / Resend.
        """
        logger.info(f"📧 Préparation de l'envoi d'e-mail à : {destinataires}")
        # Logique d'envoi réelle à implémenter ici
        return True