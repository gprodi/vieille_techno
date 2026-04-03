"""
Service dédié à la communication externe et aux rapports.
Gère le filtrage par collègue, le formatage par thème et l'envoi des newsletters.
"""
from typing import List, Dict
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
import os
import json

# 🎓 CHARGEMENT DYNAMIQUE DE L'ANNUAIRE
def charger_annuaire() -> Dict[str, List[str]]:
    chemin_fichier = "annuaire.json"
    if not os.path.exists(chemin_fichier):
        logger.error(f"Fichier de configuration '{chemin_fichier}' introuvable. Veuillez le créer.")
        return {} # Ou lever une exception : raise FileNotFoundError(...)
    
    with open(chemin_fichier, "r", encoding="utf-8") as f:
        return json.load(f)

# L'annuaire est maintenant chargé en mémoire depuis un fichier externe sécurisé
ANNUAIRE_COLLEGUES = charger_annuaire()

class ReporterService:

    @staticmethod
    def get_tous_les_mots_cles() -> List[str]:
        """Compile une liste unique de tous les centres d'intérêt de l'agence."""
        tous_les_mots = set()
        for interets in ANNUAIRE_COLLEGUES.values():
            tous_les_mots.update(interets)
        return list(tous_les_mots)

    @staticmethod
    def distribuer_veille(nouveaux_articles: List[Dict], base_url: str):
        """
        Le "Facteur" intelligent v2.0. 
        Filtre par score (>=7), limite à 3 par thème, et structure l'e-mail.
        """
        logger.info("📮 Début du tri du courrier Haute Qualité (Score >= 7) pour les collègues...")
        
        for email_collegue, interets in ANNUAIRE_COLLEGUES.items():
            articles_par_theme = {} # Un dictionnaire pour ranger les articles par tiroir (thème)
            articles_deja_selectionnes = set() # Pour éviter qu'un même article n'apparaisse dans 2 thèmes différents
            
            for mot_cle in interets:
                candidats_pour_ce_theme = []
                
                for art in nouveaux_articles:
                    # 1. Anti-doublon
                    if art['url'] in articles_deja_selectionnes:
                        continue
                        
                    # 2. Le filtre de Qualité Sévère (La note du LLM)
                    score = art.get('ai_score', 0)
                    if score < 7:
                        continue
                        
                    # 3. Vérification de la pertinence textuelle
                    texte_a_fouiller = (art.get('title', '') + " " + art.get('ai_summary', '') + " " + art.get('summary', '')).lower()
                    if mot_cle.lower() in texte_a_fouiller:
                        candidats_pour_ce_theme.append(art)
                
                # 4. On trie les candidats du meilleur score au moins bon
                candidats_pour_ce_theme.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
                
                # 5. On ne garde que le TOP 3
                top_3 = candidats_pour_ce_theme[:3]
                
                if top_3:
                    articles_par_theme[mot_cle] = top_3
                    for a in top_3:
                        articles_deja_selectionnes.add(a['url']) # On marque ces articles comme "déjà utilisés"
            
            # Si on a trouvé au moins un article qualitatif pour ce collègue
            if articles_par_theme:
                total_articles = sum(len(arts) for arts in articles_par_theme.values())
                logger.info(f"📧 Préparation d'un e-mail premium ({total_articles} articles) pour {email_collegue}...")
                corps_mail = ReporterService.generer_corps_email_par_theme(articles_par_theme, base_url, interets)
                ReporterService.envoyer_email(email_collegue, corps_mail)
            else:
                logger.debug(f"📭 Rien d'assez qualitatif aujourd'hui pour {email_collegue}.")

    @staticmethod
    def generer_corps_email_par_theme(articles_par_theme: Dict[str, List[Dict]], base_url: str, interets_collegue: List[str]) -> str:
        """Génère un e-mail HTML ultra structuré et lisible, classé par thématique."""
        
        lignes = []
        lignes.append("<div style='font-family: Arial, sans-serif; color: #333;'>")
        lignes.append("<h2 style='color: #2c3e50;'>🤖 Ta Veille Haute Qualité du Jour</h2>")
        lignes.append("<p>Bonjour ! L'IA a scruté le web et n'a retenu <strong>que les articles notés 7/10 ou plus</strong> correspondant à tes thématiques.</p>")
        lignes.append("<hr style='border: 1px solid #eee;'>")
        
        for theme, articles in articles_par_theme.items():
            # En-tête de la thématique
            lignes.append(f"<h3 style='color: #e67e22; border-bottom: 2px solid #e67e22; padding-bottom: 5px; margin-top: 30px;'>🎯 Thème : {theme.upper()}</h3>")
            
            for art in articles:
                titre = art.get('ai_french_title', art.get('title', 'Titre inconnu'))
                resume = art.get('ai_summary', art.get('summary', 'Pas de résumé disponible.'))
                url_source = art.get('url', '')
                score = art.get('ai_score', 'N/A')
                
                lignes.append(f"<h4 style='margin-bottom: 5px; color: #2980b9;'>[{score}/10] {titre}</h4>")
                # On met le résumé en italique et on gère les sauts de ligne correctement en HTML
                resume_html = resume.replace('\n', '<br>')
                lignes.append(f"<p style='font-size: 14px; line-height: 1.5; color: #555; background-color: #f9f9f9; padding: 10px; border-left: 4px solid #bdc3c7;'><i>{resume_html}</i></p>")
                
                safe_url = urllib.parse.quote_plus(url_source)
                lien_vers_app = f"{base_url}/?article_url={safe_url}"
                
                lignes.append(f"<p style='font-size: 13px;'>👉 <a href='{lien_vers_app}' style='color: #27ae60; font-weight: bold; text-decoration: none;'>Ouvrir l'analyse détaillée</a> | 🔗 <a href='{url_source}' style='color: #7f8c8d; text-decoration: none;'>Article original</a></p>")
                
        lignes.append("<br><hr style='border: 1px solid #eee;'><p style='font-size: 12px; color: #999;'>🤖 Généré automatiquement par l'Orchestrateur Llama-3.1 de l'agence.</p>")
        lignes.append("</div>")
        return "".join(lignes)

    @staticmethod
    def envoyer_email(destinataire: str, contenu_html: str):
        """Envoi SMTP."""
        expediteur = os.environ.get("SMTP_EMAIL", "ton.email@gmail.com")
        mot_de_passe = os.environ.get("SMTP_PASSWORD", "")
        
        if not mot_de_passe:
            logger.warning(f"⚠️ Simulation d'envoi à {destinataire} (Mot de passe absent).")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = expediteur
            msg['To'] = destinataire
            msg['Subject'] = "🏗️ Sélection Premium: Ta veille BIM du jour"
            
            msg.attach(MIMEText(contenu_html, 'html'))
            
            serveur = smtplib.SMTP('smtp.gmail.com', 587)
            serveur.starttls()
            serveur.login(expediteur, mot_de_passe)
            serveur.send_message(msg)
            serveur.quit()
            
            logger.success(f"✅ E-mail envoyé avec succès à {destinataire} !")
        except Exception as e:
            logger.error(f"❌ Erreur SMTP pour {destinataire} : {e}")
