import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from src.services import GoogleDriveService, TelegramBotService, IMAPService
from src.agents import SynthAgent
from src.core import ChatHistory, MailObject
from src.utils import get_logger

logger = get_logger(__name__)

class PipelineCSynthesis:
    """
    Orchestrateur du Pipeline C (Différé) : Synthèse Stratégique.
    Ce workflow s'exécute de manière asynchrone et planifiée (ex: tous les soirs à 18h).
    Il est responsable de la consolidation de la mémoire stratégique de l'établissement.
    Il agrège les e-mails de la journée et les notes vocales/textes du tampon Telegram,
    évalue leur impact via l'Agent de Synthèse (Gemini Pro), met à jour le fichier 
    "memoire_etablissement.md" (Read-Rewrite-Replace) et envoie un résumé au chef d'établissement.
    """

    def __init__(
        self,
        drive_service: GoogleDriveService,
        telegram_service: TelegramBotService,
        imap_service: IMAPService,
        synth_agent: SynthAgent,
        memoire_file_id: str
    ) -> None:
        """
        Initialise le Pipeline C avec les services et l'agent de synthèse.

        Args:
            drive_service (GoogleDriveService): Service pour manipuler memoire_etablissement.md.
            telegram_service (TelegramBotService): Service pour envoyer le résumé des modifications.
            imap_service (IMAPService): Service pour récupérer les e-mails traités/envoyés dans la journée.
            synth_agent (SynthAgent): Agent IA (Pro) capable d'analyses complexes et croisées.
            memoire_file_id (str): L'ID Google Drive du fichier Markdown de Mémoire de l'Établissement.
        """
        self.drive_service = drive_service
        self.telegram_service = telegram_service
        self.imap_service = imap_service
        self.synth_agent = synth_agent
        self.memoire_file_id = memoire_file_id
        
        self.history_file_path = Path("data/chat_history.json")

    async def run_pipeline(self) -> None:
        """
        Point d'entrée principal du traitement différé nocturne.
        Intègre le principe d'Atomicité (Acquittement / ACK).
        """
        logger.info("Début du cycle de synthèse nocturne (Pipeline C).")
        try:
            # 1. Collecte des informations (PHASE DE LECTURE SANS MARQUAGE)
            # On récupère le texte ET la liste des objets mails pour pouvoir les acquitter plus tard
            daily_info, emails_to_ack = await self._gather_daily_information()
            
            if not daily_info:
                logger.info("Aucune nouvelle information pertinente aujourd'hui. Arrêt du pipeline.")
                return

            # 2. Mise à jour de la mémoire stratégique (PHASE D'ACTION API)
            summary = await self._update_memoire_etablissement(daily_info)
            
            # 3. Finalisation (PHASE D'ACQUITTEMENT - ACK)
            # Cette phase ne s'exécute QUE si summary contient un résultat (donc si Gemini a réussi)
            if summary:
                # Acquittement 1 : On marque les messages Telegram locaux
                await self._mark_history_as_synthesized()
                
                # Acquittement 2 : On applique le flag IMAP 'CopiloteSynthetise' sur les mails traités
                if emails_to_ack:
                    await self.imap_service.mark_emails_as_synthesized(emails_to_ack)
                
                # Formatage Telegram (HTML)
                notification = f"🌙 <b>RAPPORT DE SYNTHÈSE DU SOIR</b>\n\n{summary}"
                await self.telegram_service.send_notification(notification)
                logger.info("Cycle de synthèse nocturne terminé et acquitté avec succès.")
            else:
                 logger.info("L'Agent de Synthèse a jugé qu'aucune mise à jour du fichier n'était nécessaire. Aucun message n'est marqué pour éviter les pertes.")
                 
        except Exception as e:
            # En cas de crash ici, la phase d'acquittement (ACK) n'est pas appelée.
            # Les données seront relues en toute sécurité le lendemain.
            logger.error(f"Erreur critique lors de l'exécution du Pipeline C : {e}", exc_info=True)


    # Renvoie un Tuple contenant le texte et la liste des e-mails bruts
    async def _gather_daily_information(self) -> Tuple[str, List[MailObject]]:
        """
        Récupère et agrège toutes les données brutes de la journée pour l'analyse stratégique.
        - Lit le contenu de l'historique conversationnel local.
        - Récupère les e-mails pertinents de la journée sans les marquer.
        
        Returns:
            Tuple[str, List[MailObject]]: Le texte consolidé et la liste des objets e-mails à acquitter plus tard.
        """
        logger.debug("Collecte des informations de la journée...")
        consolidated_info = ""

        # A. Collecte des notes Telegram
        telegram_notes = []
        if self.history_file_path.exists():
            try:
                content = self.history_file_path.read_text(encoding="utf-8")
                chat_history = ChatHistory.model_validate_json(content)
                
                # Filtrage : On ne garde que les messages de l'utilisateur non synthétisés
                telegram_notes = [
                    turn for turn in chat_history.turns 
                    if turn.role == "user" and not turn.est_synthetise
                ]
            except Exception as e:
                logger.error(f"Erreur lors de la lecture de {self.history_file_path} : {e}")

        if telegram_notes:
            consolidated_info += "--- NOTES TELEGRAM DE LA JOURNÉE (DICTÉES PAR LE PERDIR) ---\n"
            for note in telegram_notes:
                date_str = note.timestamp.strftime('%H:%M')
                consolidated_info += f"[{date_str}] : {note.message}\n"
            consolidated_info += "\n"

        # B. Collecte des e-mails (Appel à la méthode résiliente)
        try:
            emails_to_process = await self.imap_service.fetch_unsynthesized_emails()
        except Exception as e:
            logger.error(f"Impossible de récupérer les e-mails pour la synthèse : {e}")
            emails_to_process = []
        
        if emails_to_process:
            consolidated_info += "--- E-MAILS DE LA JOURNÉE ---\n"
            # Formatage propre des e-mails pour l'Agent de Synthèse
            for mail in emails_to_process:
                consolidated_info += f"De : {mail.expediteur}\n"
                consolidated_info += f"Sujet : {mail.sujet}\n"
                consolidated_info += f"Contenu :\n{mail.contenu_texte}\n"
                consolidated_info += "-" * 30 + "\n\n"
            
        if not telegram_notes and not emails_to_process:
             return "", []
             
        return consolidated_info, emails_to_process

    async def _update_memoire_etablissement(self, daily_info: str) -> Optional[str]:
        """
        Orchestre la mécanique 'Read-Rewrite-Replace' pour le Fichier de mémoire de l'établissement.
        """
        logger.debug("Mise à jour du fichier Mémoire Etablissement...")
        
        # 1. Read
        try:
             current_markdown = await self.drive_service.download_file_content(self.memoire_file_id)
        except Exception as e:
            logger.error(f"Impossible de lire le fichier mémoire établissement actuel : {e}")
            return None

        # 2. Rewrite
        new_markdown = await self.synth_agent.rewrite_memoire_etablissement_content(current_markdown, daily_info)
        
        if not new_markdown:
             return None
             
        # Génération du résumé des modifications
        summary = await self.synth_agent.generate_update_summary(current_markdown, new_markdown)

        # 3. Replace
        success = await self.drive_service.update_file_content(self.memoire_file_id, new_markdown)
        
        if success:
            return summary
        else:
             logger.error("Échec de la sauvegarde du nouveau fichier de mémoire établissement.")
             return None

    async def _mark_history_as_synthesized(self) -> None:
        """
        Passe le flag 'est_synthetise' à True pour tous les messages locaux.
        """
        logger.debug("Marquage de l'historique Telegram comme synthétisé...")
        if not self.history_file_path.exists():
            return
            
        try:
            content = self.history_file_path.read_text(encoding="utf-8")
            chat_history = ChatHistory.model_validate_json(content)
            
            for turn in chat_history.turns:
                turn.est_synthetise = True
                
            json_data = chat_history.model_dump_json(indent=2)
            self.history_file_path.write_text(json_data, encoding="utf-8")
        except Exception as e:
            logger.error(f"Erreur lors du marquage de l'historique Telegram : {e}")