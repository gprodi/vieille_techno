"""
Service dédié à la communication externe et aux rapports.
Gère le filtrage par collègue, le formatage et l'envoi des newsletters.
"""
from typing import List, Dict
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
import os

# 🎓 NOUVEAU : L'ANNUAIRE DE TES COLLÈGUES
# C'est ICI que tu définis qui reçoit quoi. 
# La clé est l'adresse mail, la valeur est une liste de mots-clés (centres d'intérêt).
ANNUAIRE_COLLEGUES = {
    "jean.architecte@ton-agence.fr": ["Revit", "IFC", "OpenBIM", "Maquette"],
    "marie.dev@ton-agence.fr": ["IA", "Python", "API", "Automatisation"],
    "boss@ton-agence.fr": ["Jumeau Numérique", "Start-up", "Marché", "Innovation"]
}

class ReporterService:

    @staticmethod
    def get_tous_les_mots_cles() -> List[str]:
        """
        [NOUVEAU] - Compile une liste unique de tous les centres d'intérêt de l'agence.
        Sert de 'carburant' dynamique pour l'orchestrateur (main.py).
        """
        tous_les_mots = set() # L'utilisation d'un 'set' garantit l'absence de doublons
        for interets in ANNUAIRE_COLLEGUES.values():
            tous_les_mots.update(interets)
        return list(tous_les_mots)

    @staticmethod
    def distribuer_veille(nouveaux_articles: List[Dict], base_url: str):
        """
        Le "Facteur" intelligent. Il prend tous les nouveaux articles du jour,
        regarde les intérêts de chaque collègue, et crée un mail sur mesure.
        """
        logger.info("📮 Début du tri du courrier pour les collègues...")
        
        for email_collegue, interets in ANNUAIRE_COLLEGUES.items():
            articles_pertinents = []
            
            # On vérifie chaque article pour voir s'il correspond aux intérêts de ce collègue
            for art in nouveaux_articles:
                # On regroupe le titre et le résumé pour chercher nos mots-clés dedans
                texte_a_fouiller = (art.get('title', '') + " " + art.get('summary', '')).lower()
                
                # Si au moins UN des mots-clés du collègue est dans le texte, on garde l'article !
                if any(mot_cle.lower() in texte_a_fouiller for mot_cle in interets):
                    articles_pertinents.append(art)
            
            # Si on a trouvé des articles pour lui, on génère et on envoie son mail
            if articles_pertinents:
                logger.info(f"📧 Préparation de {len(articles_pertinents)} articles pour {email_collegue}...")
                corps_mail = ReporterService.generer_corps_email(articles_pertinents, base_url, interets)
                ReporterService.envoyer_email(email_collegue, corps_mail)
            else:
                logger.debug(f"📭 Rien de pertinent pour {email_collegue} aujourd'hui.")

    @staticmethod
    def generer_corps_email(articles: List[Dict], base_url: str, interets_collegue: List[str]) -> str:
        """Génère le texte de l'e-mail avec les Deep Links vers Streamlit."""
        
        # On formate les intérêts pour les afficher dans l'intro du mail
        interets_str = ", ".join(interets_collegue)
        
        lignes = []
        lignes.append("<h2>🤖 Ta Veille Technologique Sur-Mesure</h2>")
        lignes.append(f"<p>Bonjour ! L'IA a trouvé ces articles spécifiquement basés sur tes centres d'intérêt (<strong>{interets_str}</strong>) :</p><hr>")
        
        for art in articles:
            titre = art.get('ai_french_title', art.get('title', 'Titre inconnu'))
            resume = art.get('summary', 'Pas de résumé disponible.')
            url_source = art.get('url', '')
            score = art.get('ai_score', 'N/A')
            
            lignes.append(f"<h3>📌 [{score}/10] {titre}</h3>")
            lignes.append(f"<blockquote>{resume}</blockquote>")
            
            # --- LE DEEP LINK ---
            safe_url = urllib.parse.quote_plus(url_source)
            lien_vers_app = f"{base_url}/?article_url={safe_url}"
            
            lignes.append(f"<p>👉 <strong><a href='{lien_vers_app}'>Ouvrir le Grand Résumé IA dans l'application</a></strong></p>")
            lignes.append(f"<p>🔗 <em><a href='{url_source}'>Voir l'article source original</a></em></p><br>")
            
        return "".join(lignes)

    @staticmethod
    def envoyer_email(destinataire: str, contenu_html: str):
        """
        Envoi réel du mail via SMTP.
        Nécessite SMTP_EMAIL et SMTP_PASSWORD dans les variables d'environnement.
        """
        expediteur = os.environ.get("SMTP_EMAIL", "ton.email@gmail.com")
        mot_de_passe = os.environ.get("SMTP_PASSWORD", "")
        
        if not mot_de_passe:
            logger.warning(f"⚠️ Simulation d'envoi à {destinataire} (SMTP_PASSWORD non configuré).")
            return

        try:
            # Création du message
            msg = MIMEMultipart()
            msg['From'] = expediteur
            msg['To'] = destinataire
            msg['Subject'] = "🏗️ Ton rapport de veille personnalisé"
            
            msg.attach(MIMEText(contenu_html, 'html'))
            
            # Connexion au serveur SMTP (Exemple ici avec Gmail)
            # Si tu utilises Outlook : smtp.office365.com (port 587)
            serveur = smtplib.SMTP('smtp.gmail.com', 587)
            serveur.starttls()
            serveur.login(expediteur, mot_de_passe)
            serveur.send_message(msg)
            serveur.quit()
            
            logger.success(f"✅ E-mail envoyé avec succès à {destinataire} !")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi de l'e-mail à {destinataire} : {e}")