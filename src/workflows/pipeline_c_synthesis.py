import json
import difflib
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from src.services import GoogleDriveService, TelegramBotService, IMAPService
from src.core.dependencies import get_token_tracker_service
from src.agents import SynthAgent
from src.core import ChatHistory, MailObject
from src.utils import get_logger
from src.utils import get_logger, truncate_text_for_llm
from src.workflows.pipeline_b_telegram import PipelineBTelegram

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
        memoire_file_id: str,
        pipeline_b: PipelineBTelegram = None,
    ) -> None:
        """
        Initialise le Pipeline C avec les services et l'agent de synthèse.

        Args:
            drive_service (GoogleDriveService): Service pour manipuler memoire_etablissement.md.
            telegram_service (TelegramBotService): Service pour envoyer le résumé des modifications.
            imap_service (IMAPService): Service pour récupérer les e-mails traités/envoyés dans la journée.
            synth_agent (SynthAgent): Agent IA (Pro) capable d'analyses complexes et croisées.
            memoire_file_id (str): L'ID Google Drive du fichier html de Mémoire de l'Établissement.
        """
        self.drive_service = drive_service
        self.telegram_service = telegram_service
        self.imap_service = imap_service
        self.synth_agent = synth_agent
        self.memoire_file_id = memoire_file_id
        self.pipeline_b = pipeline_b
        self.historique_en_cours_de_traitement = []
        
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

                # Ajout du rapport financier quotidien
                try:
                    tracker = get_token_tracker_service()
                    # On fixe la date de début à aujourd'hui à 00:00:00
                    aujourdhui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    stats_jour = await tracker.get_stats(start_date=aujourdhui)
                    
                    if stats_jour:
                        notification += "\n\n📊 <b>Conso API du jour</b>\n"
                        total_cost = 0.0
                        
                        for modele, data in stats_jour.items():
                            in_t, out_t = data['input'], data['output']
                            
                            from src.core.config import get_settings
                            settings = get_settings()
                            
                            if "pro" in modele.lower():
                                cost = (in_t * settings.PRICE_PRO_INPUT / 1000000) + (out_t * settings.PRICE_PRO_OUTPUT / 1000000)
                            elif "lite" in modele.lower():
                                cost = (in_t * settings.PRICE_FLASH_LITE_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_LITE_OUTPUT / 1000000)
                            else:
                                cost = (in_t * settings.PRICE_FLASH_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_OUTPUT / 1000000)
                                
                            total_cost += cost
                            # Formatage des nombres avec des espaces pour les milliers
                            tokens_str = f"{data['total']:,}".replace(',', ' ')
                            notification += f"- <i>{modele}</i> : {tokens_str} tokens\n"
                            
                        notification += f"<b>Coût estimé :</b> ~{total_cost:.4f} $\n"
                except Exception as e:
                    logger.error(f"Erreur lors de la génération du rapport financier : {e}")


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

        # A. Collecte de la conversation Telegram directement depuis la RAM du Pipeline B
        telegram_notes = []
        if self.pipeline_b and self.pipeline_b.chat_history:
            # Filtrage : On garde TOUS les messages (user ET model) non synthétisés
            telegram_notes = [
                turn for turn in self.pipeline_b.chat_history.turns 
                if not turn.est_synthetise
            ]
            self.historique_en_cours_de_traitement = telegram_notes

        if telegram_notes:
            consolidated_info += "--- ÉCHANGES TELEGRAM DE LA JOURNÉE (PERDIR & COPILOTE IA) ---\n"
            for note in telegram_notes:
                date_str = note.timestamp.strftime('%H:%M')
                
                # On identifie clairement qui parle pour aider l'Agent de Synthèse
                auteur = "Perdir" if note.role == "user" else "Copilote IA"
                
                consolidated_info += f"[{date_str}] {auteur} : {note.message}\n"
            consolidated_info += "\n"

        # B. Collecte des e-mails (Appel à la méthode résiliente)
        try:
            emails_to_process = await self.imap_service.fetch_unsynthesized_emails(limit_per_folder=250)
        except Exception as e:
            logger.error(f"Impossible de récupérer les e-mails pour la synthèse : {e}")
            emails_to_process = []
        
        if emails_to_process:
            consolidated_info += "--- E-MAILS DE LA JOURNÉE ---\n"
            # Formatage propre des e-mails pour l'Agent de Synthèse
            for mail in emails_to_process:
                consolidated_info += f"De : {mail.expediteur}\n"
                consolidated_info += f"Sujet : {mail.sujet}\n"
                contenu_tronque = truncate_text_for_llm(mail.contenu_texte, max_tokens=800)
                consolidated_info += f"Contenu :\n{contenu_tronque}\n"
                consolidated_info += "-" * 30 + "\n\n"
            
        if not telegram_notes and not emails_to_process:
             return "", []
             
        return consolidated_info, emails_to_process

    async def _update_memoire_etablissement(self, daily_info: str) -> Optional[str]:
        """
        Orchestre la mécanique 'Read-Rewrite-Replace' pour le Fichier de mémoire de l'établissement.
        """
        logger.debug("Mise à jour du fichier Mémoire Etablissement (Google Doc)...")
        
        # 1. Read
        try:
             current_html = await self.drive_service.export_google_doc_as_html(self.memoire_file_id)
        except Exception as e:
            logger.error(f"Impossible de lire le fichier mémoire établissement actuel : {e}")
            return None

        # --- SAUVEGARDE DE SÉCURITÉ LOCALE (BACKUP) ---
        try:
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            nom_backup = f"memoire_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            backup_file = backup_dir / nom_backup
            backup_file.write_text(current_html, encoding="utf-8")
            logger.debug(f"Sauvegarde locale de la mémoire effectuée : {backup_file}")
        except Exception as e:
            logger.warning(f"Échec de la création du backup local : {e}")
            nom_backup = "Erreur de backup"

        # 2. Rewrite
        new_html = await self.synth_agent.rewrite_memoire_etablissement_content(current_html, daily_info)
        
        if not new_html:
             return None


        # --- Contrôle d'intégrité (Sanity Check) Non-bloquant ---
        alertes = []
        
        # Vérification 1 : Amputation massive du texte
        if len(new_html) < (len(current_html) * 0.70):
            alertes.append(f"- Perte de volume suspecte (Ancien: {len(current_html)} chars, Nouveau: {len(new_html)} chars).")
            
        # Vérification 2 : Calcul du taux de similarité
        similarity_ratio = difflib.SequenceMatcher(None, current_html, new_html).ratio()
        if similarity_ratio < 0.60:
            alertes.append(f"- Taux de similarité très faible ({similarity_ratio:.2f}). Réécriture potentiellement excessive.")

        # Si une anomalie est détectée, on envoie une notification immédiate
        if alertes:
            lignes_alerte = "\n".join(alertes)
            msg_alerte = (
                "⚠️ <b>ALERTE INTÉGRITÉ - MÉMOIRE DE L'ÉTABLISSEMENT</b> ⚠️\n\n"
                "La mise à jour de ce soir présente des modifications suspectes :\n"
                f"{lignes_alerte}\n\n"
                "Le fichier a tout de même été mis à jour sur votre Drive, mais la version d'hier "
                f"a été sauvegardée sur le Raspberry Pi sous le nom : <i>{nom_backup}</i>.\n"
                "Je vous invite à vérifier le document."
            )
            await self.telegram_service.send_notification(msg_alerte)
            logger.warning("Alerte intégrité envoyée sur Telegram, mais l'écrasement se poursuit.")
             
        # Génération du résumé des modifications
        summary = await self.synth_agent.generate_update_summary(current_html, new_html)

        # 3. Replace
        success = await self.drive_service.update_file_content(self.memoire_file_id, new_html)
        
        if success:
            return summary
        else:
             logger.error("Échec de la sauvegarde du nouveau fichier de mémoire établissement.")
             return None

    async def _mark_history_as_synthesized(self) -> None:
        """
        Passe le flag 'est_synthetise' à True directement dans la mémoire du Pipeline B.
        """
        logger.debug("Marquage de l'historique Telegram comme synthétisé en RAM...")
        if not self.pipeline_b:
            return
            
        try:
            # On utilise le verrou du Pipeline B pour éviter la collision
            async with self.pipeline_b._memory_lock:
                # On modifie les objets directement en mémoire vive
                for turn in self.historique_en_cours_de_traitement:
                    turn.est_synthetise = True
                    
                # On demande au Pipeline B de sauvegarder proprement sa mémoire sur le disque
                self.pipeline_b._save_history()
                
            # On vide le cache (en dehors du verrou, ce n'est plus risqué)
            self.historique_en_cours_de_traitement = []
            
        except Exception as e:
            logger.error(f"Erreur lors du marquage de l'historique Telegram : {e}")