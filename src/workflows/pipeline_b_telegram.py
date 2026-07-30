from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.services.telegram_bot import TelegramBotService
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.google_drive_api import GoogleDriveService
from src.services.google_calendar_tasks import GoogleCalendarTasksService

from src.agents.router_agent import RouterAgent
from src.agents.rag_agent import RAGAgent
from src.agents.briefing_agent import BriefingAgent
from src.agents.main_courante_agent import MainCouranteAgent

from src.core.models import RouteChoice
from src.utils.logger import get_logger

import os
from google import genai
from src.core.config import get_settings
from datetime import datetime

# Initialisation du logger
logger = get_logger(__name__)

class PipelineBTelegram:
    """
    Orchestrateur du Pipeline B (Actif) : Assistant Interactif Telegram.
    
    Ce workflow est déclenché par la réception d'un message (texte ou audio) 
    du chef d'établissement. Il délègue la compréhension de l'intention à 
    l'Agent Routeur, puis exécute l'une des 5 routes possibles :
    1. Agenda (Tâches/Calendrier)
    2. Recherche RAG (Interrogation de la mémoire vectorielle)
    3. Briefing (Synthèse des e-mails)
    4. Saisie Main Courante (Enregistrement d'un incident)
    5. Info Stratégique (Mise en mémoire tampon pour le traitement du soir)
    """

    def __init__(
        self,
        telegram_service: TelegramBotService,
        imap_service: IMAPService,
        chroma_service: ChromaDBService,
        drive_service: GoogleDriveService,
        calendar_service: GoogleCalendarTasksService,
        router_agent: RouterAgent,
        rag_agent: RAGAgent,
        briefing_agent: BriefingAgent,
        main_courante_agent: MainCouranteAgent
    ) -> None:
        """
        Initialise le Pipeline B avec tous les services et agents nécessaires 
        aux différentes routes conversationnelles.

        Args:
            telegram_service (TelegramBotService): Service pour répondre à l'utilisateur.
            imap_service (IMAPService): Pour la lecture des e-mails (Route Briefing).
            chroma_service (ChromaDBService): Base vectorielle (Route RAG).
            drive_service (GoogleDriveService): Accès au Drive (Main Courante & Tampon).
            calendar_service (GoogleCalendarTasksService): Gestion de l'agenda (Route Agenda).
            router_agent (RouterAgent): Agent standardiste (classification de l'intention).
            rag_agent (RAGAgent): Agent de synthèse documentaire.
            briefing_agent (BriefingAgent): Agent spécialisé dans le résumé d'inbox.
            main_courante_agent (MainCouranteAgent): Agent de formatage d'incidents.
        """
        self.telegram_service = telegram_service
        self.imap_service = imap_service
        self.chroma_service = chroma_service
        self.drive_service = drive_service
        self.calendar_service = calendar_service
        
        self.router_agent = router_agent
        self.rag_agent = rag_agent
        self.briefing_agent = briefing_agent
        self.main_courante_agent = main_courante_agent

        # On attache automatiquement la méthode de traitement au service Telegram
        self.telegram_service.register_message_handler(self.process_telegram_message)
        logger.debug("Pipeline B (Telegram) initialisé et gestionnaire enregistré.")

    async def process_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Point d'entrée principal appelé par le TelegramBotService lors de la 
        réception d'un message non-commande.
        
        Étapes :
        - Extraction du texte (ou transcription si c'est un message vocal).
        - Appel du RouterAgent pour déterminer la route métier à emprunter.
        - Aiguillage (switch/match) vers la méthode `_handle_*_route` correspondante.
        - Gestion globale des erreurs avec retour utilisateur bienveillant en cas d'échec.

        Args:
            update (Update): L'objet Update fourni par l'API Telegram.
            context (ContextTypes.DEFAULT_TYPE): Le contexte d'exécution Telegram.
        """

        # --- CLAUSE DE GARDE ---
        # Si le message est une édition d'un message existant, on ignore pour éviter les doublons.
        if update.edited_message:
            logger.info("Message édité ignoré pour éviter la duplication des actions.")
            return
        # -----------------------

        try:
            # 1. Extraction du texte (Gestion basique pour le moment)
            if update.message.voice:
                # Création d'un nom de fichier temporaire unique basé sur l'ID du message
                voice_file_path = f"temp_voice_{update.message.message_id}.ogg"
                
                try:
                    # Notification visuelle pour faire patienter l'utilisateur
                    await update.message.reply_text("🎙️ <i>Écoute et transcription en cours...</i>", parse_mode=ParseMode.HTML)
                    
                    # Téléchargement local du fichier via l'API Telegram
                    voice_file = await update.message.voice.get_file()
                    await voice_file.download_to_drive(voice_file_path)
                    
                    # Initialisation du client Gemini à la volée
                    settings = get_settings()
                    client = genai.Client(api_key=settings.GEMINI_API_KEY)
                    
                    # Upload du fichier audio sur les serveurs Gemini
                    uploaded_audio = await client.aio.files.upload(file=voice_file_path)
                    
                    # Prompt strict pour forcer une transcription brute
                    transcription_prompt = (
                        "Retranscris exactement le contenu de ce message vocal, mot pour mot. "
                        "N'ajoute aucune introduction, aucune conclusion, et aucun commentaire."
                    )
                    
                    # Génération du contenu textuel
                    response = await client.aio.models.generate_content(
                        model=settings.GEMINI_FLASH_MODEL,
                        contents=[uploaded_audio, transcription_prompt]
                    )
                    
                    if not response.text:
                        raise ValueError("L'IA a renvoyé une transcription vide.")
                        
                    user_text = response.text.strip()
                    logger.info(f"Transcription audio réussie : '{user_text}'")
                    
                    # Suppression du fichier sur les serveurs de Google (Bonne pratique)
                    await client.aio.files.delete(name=uploaded_audio.name)
                    
                except Exception as e:
                    logger.error(f"Échec de la transcription du fichier audio : {e}", exc_info=True)
                    await update.message.reply_text("❌ <b>Erreur</b> : Impossible de transcrire votre message vocal. Veuillez réessayer ou écrire votre message.", parse_mode=ParseMode.HTML)
                    return
                finally:
                    # Nettoyage du fichier local de manière sécurisée
                    if os.path.exists(voice_file_path):
                        os.remove(voice_file_path)
                        logger.debug(f"Fichier temporaire {voice_file_path} supprimé du disque.")
            elif update.message.text:
                user_text = update.message.text
            else:
                await update.message.reply_text("⚠️ Veuillez m'envoyer un message textuel ou vocal.")
                return

            logger.info(f"Message reçu pour aiguillage : '{user_text}'")

            # 2. Appel de l'Agent Routeur pour la classification de l'intention
            routes, explication = await self.router_agent.classify_intent(user_text)

            # 3. Construction du message de confirmation visuelle (pour l'étape de test actuelle)
            routes_str = ", ".join([r.value for r in routes])
            debug_message = f"🚦 <b>Aiguillage IA terminé</b>\n<b>Routes détectées :</b> {routes_str}"
            
            if explication:
                debug_message += f"\n\n<i>Explication de l'IA : {explication}</i>"

            # Réponse directe au message de l'utilisateur sur Telegram
            await update.message.reply_text(debug_message, parse_mode=ParseMode.HTML)

            # 4. Aiguillage (Routing) dynamique des actions
            for route in routes:
                if route == RouteChoice.AGENDA:
                    await self._handle_agenda_route(user_text)
                elif route == RouteChoice.RAG_SEARCH:
                    await self._handle_rag_search_route(user_text)
                elif route == RouteChoice.BRIEFING:
                    await self._handle_briefing_route(user_text)
                elif route == RouteChoice.MAIN_COURANTE:
                    await self._handle_main_courante_route(user_text)
                elif route == RouteChoice.STRATEGIC_BUFFER:
                    await self._handle_strategic_buffer_route(user_text)
                elif route == RouteChoice.AUCUN_OU_INCOMPLET:
                    # Traité visuellement via l'explication, aucune action métier additionnelle
                    logger.info("Route 'aucun_ou_incomplet' atteinte.")

        except Exception as e:
            logger.error(f"Erreur critique lors du traitement du message Telegram : {e}", exc_info=True)
            await update.message.reply_text("❌ <b>Erreur interne</b> : Impossible de traiter votre demande.", parse_mode=ParseMode.HTML)

    async def _handle_agenda_route(self, user_text: str) -> None:
        """
        Gère la route "Agenda".
        Analyse la demande pour créer une tâche Google Tasks ou générer 
        un lien de création d'événement Google Calendar pré-rempli.
        Notifie l'utilisateur du succès sur Telegram.

        Args:
            user_text (str): La requête brute de l'utilisateur.
        """
        logger.info("Exécution de la route : AGENDA")

    async def _handle_rag_search_route(self, user_text: str) -> None:
        """
        Gère la route "Recherche RAG".
        Vectorise la question, extrait les e-mails pertinents via ChromaDBService,
        soumet le contexte au RAGAgent pour formuler une réponse, et l'envoie sur Telegram.

        Args:
            user_text (str): La question posée par l'utilisateur.
        """
        pass

    async def _handle_briefing_route(self, user_text: str) -> None:
        """
        Gère la route "Briefing".
        Récupère les e-mails pertinents (urgents ou non lus) via IMAPService,
        fait appel au BriefingAgent pour générer un résumé structuré, et l'envoie sur Telegram.

        Args:
            user_text (str): La demande de l'utilisateur (peut inclure des précisions 
                             comme "donne-moi juste les urgences").
        """
        pass

    async def _handle_main_courante_route(self, user_text: str) -> None:
        """
        Gère la route "Saisie Main Courante" déclenchée manuellement via Telegram.
        Fait appel au MainCouranteAgent pour formater le texte brut en incident professionnel,
        puis l'ajoute au fichier Main_Courante.md via le GoogleDriveService.

        Args:
            user_text (str): La description factuelle de l'incident dictée par le Perdir.
        """
        pass

    async def _handle_strategic_buffer_route(self, user_text: str) -> None:
        """
        Gère la route "Info Stratégique (Tampon)".
        Enregistre une réflexion ou une information clé dans le fichier temporaire 
        'Tampon_Telegram.txt' sur Google Drive en attendant le traitement différé du Pipeline C.
        Confirme la bonne prise en compte à l'utilisateur.

        Args:
            user_text (str): L'information ou la réflexion stratégique à sauvegarder.
        """
        logger.info("Exécution de la route : INFO STRATÉGIQUE (TAMPON)")
        
        try:
            # 1. Recherche du fichier tampon sur le Drive par son nom
            file_name = "Tampon_Telegram.txt"
            file_id = await self.drive_service.find_file_or_folder(file_name)
            
            if not file_id:
                logger.error(f"Le fichier '{file_name}' est introuvable sur le Drive.")
                await self.telegram_service.send_notification(
                    f"❌ <b>Erreur :</b> Le fichier <i>{file_name}</i> est introuvable sur Google Drive. "
                    "Veuillez le créer à la racine du dossier."
                )
                return

            # 2. Téléchargement du contenu actuel
            current_content = await self.drive_service.download_file_content(file_id)
            
            # 3. Formatage de la nouvelle entrée avec horodatage
            timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M")
            new_entry = f"\n\n--- Note du {timestamp} ---\n{user_text}"
            
            # 4. Concaténation (si le fichier est vide, on évite les sauts de ligne initiaux)
            if current_content and current_content.strip():
                updated_content = current_content + new_entry
            else:
                updated_content = new_entry.strip()

            # 5. Mise à jour (écrasement) du fichier sur le Drive
            success = await self.drive_service.update_file_content(file_id, updated_content)
            
            # 6. Notification de confirmation au chef d'établissement
            if success:
                logger.info("L'information stratégique a bien été ajoutée au tampon.")
                confirmation_msg = (
                    "✅ <b>Info stratégique enregistrée.</b>\n"
                    "Elle sera prise en compte lors de la synthèse de ce soir."
                )
                await self.telegram_service.send_notification(confirmation_msg)
            else:
                logger.warning("Échec silencieux lors de l'écrasement du fichier Tampon sur le Drive.")
                await self.telegram_service.send_notification("❌ <b>Erreur :</b> La sauvegarde sur le Drive a échoué.")
                
        except Exception as e:
            logger.error(f"Erreur inattendue dans la route Info Stratégique : {e}", exc_info=True)
            await self.telegram_service.send_notification("❌ <b>Erreur système :</b> Impossible de traiter l'information stratégique.")