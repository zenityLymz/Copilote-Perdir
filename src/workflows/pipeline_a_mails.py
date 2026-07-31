import asyncio
from datetime import datetime
from typing import List, Optional
import html

from src.core import MailObject, TriDecision, get_settings
from src.services import IMAPService, ChromaDBService, TelegramBotService
from src.agents import TriageAgent
from src.utils import get_logger

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class PipelineAMails:
    """
    Orchestrateur du Pipeline A (Passif) : Traitement Automatique des E-mails.
    
    Ce workflow écoute la boîte IMAP en tâche de fond, soumet les nouveaux e-mails 
    à l'Agent de Triage, et exécute automatiquement jusqu'à 3 actions :
    1. Alerte Telegram immédiate (si urgence).
    2. Déplacement de l'e-mail dans le bon dossier IMAP et tagging pour indiquer que le mail a été traité par le bot.
    3. Indexation dans la base vectorielle ChromaDB (sauf poubelle).
    """

    def __init__(
        self,
        imap_service: IMAPService,
        triage_agent: TriageAgent,
        chroma_service: ChromaDBService,
        telegram_service: TelegramBotService
    ) -> None:
        """
        Initialise le Pipeline A avec l'ensemble des services et agents requis.
        L'injection de dépendances permet un découplage total de la logique métier.
        """
        self.imap_service = imap_service
        self.triage_agent = triage_agent
        self.chroma_service = chroma_service
        self.telegram_service = telegram_service
        
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
                    # Temporisation défensive pour préserver les quotas de l'API Gemini
                    settings = get_settings()
                    await asyncio.sleep(settings.GEMINI_API_PAUSE_SECONDS)
                    
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
            # On "échappe" les chevrons < et > pour ne pas faire planter le HTML de Telegram
            expediteur_safe = html.escape(mail.expediteur)
            sujet_safe = html.escape(mail.sujet)
            justification_safe = html.escape(decision.justification)

            alerte_msg = (
                f"🚨 <b>URGENCE MAIL</b> 🚨\n\n"
                f"<b>De :</b> {expediteur_safe}\n"
                f"<b>Sujet :</b> {sujet_safe}\n\n"
                f"<b>Analyse IA :</b> {justification_safe}"
            )
            await self.telegram_service.send_notification(alerte_msg)

        # Action 2 : Indexation ChromaDB (ignorée si le dossier cible est "Trash")
        if decision.dossier_cible.value != "Trash":
            await self.chroma_service.index_emails([mail])
        else:
            logger.debug(f"E-mail {mail.id_mail} ignoré pour l'indexation (classé Trash).")

        # Action FINALE : Validation (Déplacement si nécessaire et Tag pour indiquer que le mail a été traité)
        logger.debug(f"Ajout du tag de traitement pour l'e-mail {mail.id_mail}")
        await self.imap_service.mark_as_processed(mail.id_mail)

        # 2. On déplace le mail uniquement si nécessaire
        if decision.dossier_cible.value != "INBOX":
            await self.imap_service.move_email(decision)

        logger.info(f"Traitement complet terminé pour l'e-mail {mail.id_mail}.")