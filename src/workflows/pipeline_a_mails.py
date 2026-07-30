import asyncio
import re
from datetime import datetime
from typing import List, Optional

from src.core.models import MailObject, TriDecision
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.telegram_bot import TelegramBotService
from src.services.google_drive_api import GoogleDriveService
from src.agents.triage_agent import TriageAgent
from src.agents.main_courante_agent import MainCouranteAgent
from src.utils.logger import get_logger
from src.core.config import get_settings

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class PipelineAMails:
    """
    Orchestrateur du Pipeline A (Passif) : Traitement Automatique des E-mails.
    
    Ce workflow écoute la boîte IMAP en tâche de fond, soumet les nouveaux e-mails 
    à l'Agent de Triage, et exécute automatiquement jusqu'à 4 actions :
    1. Alerte Telegram immédiate (si urgence).
    2. Déplacement de l'e-mail dans le bon dossier IMAP.
    3. Indexation dans la base vectorielle ChromaDB (sauf poubelle).
    4. Enregistrement d'un incident dans la Main Courante (si pertinent).
    """

    def __init__(
        self,
        imap_service: IMAPService,
        triage_agent: TriageAgent,
        chroma_service: ChromaDBService,
        telegram_service: TelegramBotService,
        drive_service: GoogleDriveService,
        main_courante_agent: MainCouranteAgent
    ) -> None:
        """
        Initialise le Pipeline A avec l'ensemble des services et agents requis.
        L'injection de dépendances permet un découplage total de la logique métier.
        """
        self.imap_service = imap_service
        self.triage_agent = triage_agent
        self.chroma_service = chroma_service
        self.telegram_service = telegram_service
        self.drive_service = drive_service
        self.main_courante_agent = main_courante_agent
        
        logger.debug("Pipeline A (Mails) initialisé avec ses dépendances.")

    async def run_pipeline(self, folder: str = "INBOX", limit: int = 50) -> None:
        """
        Point d'entrée principal de la boucle de traitement des e-mails.
        Destiné à être appelé à intervalles réguliers (polling non-bloquant).
        """
        logger.info(f"Démarrage d'un cycle de traitement du Pipeline A sur le dossier '{folder}'.")
        
        try:
            # 1. Récupération des e-mails non lus
            emails: List[MailObject] = await self.imap_service.fetch_unread_emails(folder=folder, limit=limit)
            
            if not emails:
                logger.debug("Aucun nouvel e-mail à traiter lors de ce cycle.")
                return
                
            logger.info(f"{len(emails)} nouvel/nouveaux e-mail(s) récupéré(s). Début du triage.")

            # 2. Itération et traitement individuel
            for mail in emails:
                try:
                    await self._process_single_mail(mail)
                except Exception as e:
                    logger.error(f"Échec inattendu lors du traitement de l'e-mail ID {mail.id_mail} : {e}", exc_info=True)
                finally:
                    # Temporisation défensive pour préserver les quotas de l'API Gemini (ex: 30 requêtes / minute)
                    await asyncio.sleep(2)
                    
            logger.info("Cycle du Pipeline A terminé avec succès.")
            
        except Exception as e:
            logger.error(f"Erreur critique lors de l'exécution du Pipeline A : {e}", exc_info=True)


    async def _process_single_mail(self, mail: MailObject) -> None:
        """
        Sous-routine traitant le cycle de vie complet d'un unique e-mail entrant.
        """
        logger.debug(f"Traitement de l'e-mail: {mail.sujet}")

        # 1. Triage par l'IA
        decision: TriDecision = await self.triage_agent.evaluate_email(mail)

        # Action 1 : Notification Telegram (si critique)
        if decision.necessite_notification:
            alerte_msg = (
                f"🚨 **URGENCE MAIL** 🚨\n\n"
                f"**De :** {mail.expediteur}\n"
                f"**Sujet :** {mail.sujet}\n\n"
                f"**Analyse IA :** {decision.justification}"
            )
            await self.telegram_service.send_notification(alerte_msg)

        # Action 2 : Déplacement IMAP vers le dossier cible
        await self.imap_service.move_email(decision)

        # Action 3 : Indexation ChromaDB (ignorée si le dossier cible est "TRASH")
        if decision.dossier_cible != "TRASH":
            await self.chroma_service.index_emails([mail])
        else:
            logger.debug(f"E-mail {mail.id_mail} ignoré pour l'indexation (classé TRASH).")

        # Action 4 : Appel conditionnel à l'Agent Main Courante
        if decision.necessite_main_courante:
            await self._trigger_main_courante(mail)

        logger.info(f"Traitement complet terminé pour l'e-mail {mail.id_mail}.")


    async def _trigger_main_courante(self, mail: MailObject) -> bool:
        """
        Gère la mécanique "Read-Append-Replace" pour tracer un incident issu d'un e-mail.
        """
        logger.info(f"Déclenchement de la rédaction Main Courante pour l'e-mail {mail.id_mail}.")
        
        settings = get_settings()
        file_id = settings.MAIN_COURANTE_FILE_ID
        
        try:
            # 1. READ : Téléchargement du contenu actuel
            current_content = await self.drive_service.download_file_content(file_id)
            
            # Extraction des tags existants (#Catégories et @Personnes) pour la cohérence
            existing_tags = list(set(re.findall(r'[#@]\w+', current_content)))

            # 2. GENERATE : Création de la nouvelle entrée par l'IA
            nouvelle_entree = await self.main_courante_agent.format_from_mail(mail, existing_tags=existing_tags)
            
            # Injection de l'horodatage et de l'origine par Python (100% FIABLE)
            date_enregistrement = datetime.now().strftime("%d/%m/%Y à %H:%M")
            origine_info = f"E-mail reçu de {mail.expediteur} - Objet : {mail.sujet}"
            
            # Concaténation brute et sûre des puces Python avec les puces de l'IA
            entree_finale = (
                f"- **Enregistré le :** {date_enregistrement}\n"
                f"- **Origine de l'information :** {origine_info}\n"
                f"{nouvelle_entree}"
            )
            
            # 3. APPEND : Concaténation de la nouvelle entrée à la fin du document
            # Ajout d'une séparation visuelle (---) entre chaque entrée
            new_content = current_content.strip() + "\n\n---\n\n" + entree_finale
            
            # 4. REPLACE : Écrasement du fichier sur le Drive
            success = await self.drive_service.update_file_content(file_id, new_content)
            
            if success:
                logger.info("Incident ajouté avec succès à la Main Courante.")
                return True
            else:
                logger.warning("L'ajout à la Main Courante a échoué lors de l'upload Drive.")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la Main Courante : {e}", exc_info=True)
            return False