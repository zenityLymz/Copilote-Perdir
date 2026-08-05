import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from src.utils import get_logger
from src.agents import OrchestratorAgent
from src.services import TelegramBotService
from src.core import ChatHistory, ConversationTurn, get_settings
from src.utils import split_telegram_message
from src.core.dependencies import get_gemini_router_service

# Initialisation du logger
logger = get_logger(__name__)

class PipelineBTelegram:
    """
    Orchestrateur du Pipeline B (Actif) : Assistant Interactif Telegram.
    
    Ce workflow est déclenché par la réception d'un message (texte ou audio) 
    du chef d'établissement. Il maintient l'état de la conversation (ChatHistory) 
    pour conserver le contexte et délègue le raisonnement et l'action 
    à l'OrchestratorAgent. La mémoire est persistée localement.
    """

    def __init__(self, telegram_service: TelegramBotService, orchestrator_agent: OrchestratorAgent) -> None:
        """
        Initialise le Pipeline B en y injectant le service de communication et le cerveau agentique.

        Args:
            telegram_service (TelegramBotService): Le service gérant l'envoi de messages sur Telegram.
            orchestrator_agent (OrchestratorAgent): L'agent autonome gérant la logique et les outils.
        """
        self.telegram_service = telegram_service
        self.orchestrator_agent = orchestrator_agent
        self.history_file_path = Path("data/chat_history.json")
        self._memory_lock = asyncio.Lock()
        
        # Restauration ou initialisation de la mémoire locale de la conversation
        if self.history_file_path.exists():
            try:
                content = self.history_file_path.read_text(encoding="utf-8")
                self.chat_history = ChatHistory.model_validate_json(content)
                logger.info("Historique conversationnel restauré avec succès depuis le fichier local.")
            except Exception as e:
                logger.error(f"Fichier d'historique corrompu ou invalide, réinitialisation de la mémoire : {e}")
                self.chat_history = ChatHistory()
        else:
            self.chat_history = ChatHistory()
            logger.info("Aucun historique local trouvé, initialisation d'une nouvelle mémoire conversationnelle.")
        
        logger.debug("Pipeline B (Telegram) initialisé avec ses dépendances.")


    async def process_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Point d'entrée asynchrone interceptant les messages Telegram du Perdir.
        S'occupe d'extraire le texte (ou transcrire le vocal), de mettre à jour 
        la mémoire, d'interroger l'Orchestrateur et de renvoyer la réponse.

        Args:
            update (Update): L'objet natif Telegram contenant le message.
            context (ContextTypes.DEFAULT_TYPE): Le contexte d'exécution de python-telegram-bot.
        """
        if not update.message:
            return

        user_text = ""

        # 1. Extraire le message texte (ou préparer la transcription du vocal)
        if update.message.text:
            user_text = update.message.text
        elif update.message.voice or update.message.audio:
            # Notification pour faire patienter l'utilisateur pendant l'écoute
            await update.message.reply_text("<i>🎤 J'écoute votre message vocal...</i>", parse_mode=ParseMode.HTML)
            
            try:
                # Appel de notre nouvelle méthode en RAM
                user_text = await self._transcribe_audio(update)
                # Affichage de la transcription pour validation visuelle
                #await update.message.reply_text(f"<i>📝 Transcription : \"{user_text}\"</i>", parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Échec de la transcription audio : {e}")
                await update.message.reply_text("⚠️ Désolé, je n'ai pas réussi à analyser ce message vocal.")
                return
        else:
            logger.warning("Format de message non supporté.")
            await update.message.reply_text("Désolé, je ne peux traiter que du texte ou des mémos vocaux.")
            return

        logger.debug(f"Requête utilisateur extraite : {user_text}")

        # 2. Mettre à jour la mémoire et sauvegarder
        async with self._memory_lock:
            self.chat_history.turns.append(
                ConversationTurn(role="user", message=user_text)
            )
            self._save_history()

        try:
            # Afficher l'indicateur "Le bot est en train d'écrire..." pour faire patienter l'utilisateur
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # 3. Interroger l'Orchestrateur (qui va réfléchir, utiliser ses outils si besoin et répondre)
            ai_response = await self.orchestrator_agent.process_user_request(
                user_message=user_text, 
                chat_history=self.chat_history
            )
            
            # 4. Mettre à jour la mémoire avec la réponse IA et sauvegarder
            async with self._memory_lock:
                self.chat_history.turns.append(
                    ConversationTurn(role="model", message=ai_response)
                )
                self._save_history()
            
            # 5. Renvoyer la réponse de l'IA au chef d'établissement
            # Utilisation de text_utils pour éviter de crasher sur la limite de caractères Telegram (4096)
            response_chunks = split_telegram_message(ai_response)
            for chunk in response_chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
                
        except Exception as e:
            logger.error(f"Erreur critique lors du traitement du message par l'Orchestrateur : {e}", exc_info=True)
            await update.message.reply_text("⚠️ Désolé, une erreur technique m'a empêché de traiter votre demande. Veuillez réessayer.")

    async def _transcribe_audio(self, update: Update) -> str:
        """
        Télécharge le message vocal Telegram en mémoire et utilise Gemini Flash 
        pour le transcrire en texte.
        """
        from google import genai
        from google.genai import types
        from src.core.config import get_settings
        
        # 1. Récupération des métadonnées du fichier audio/vocal
        audio_attachment = update.message.voice or update.message.audio
        telegram_file = await update.get_bot().get_file(audio_attachment.file_id)
        
        # 2. Téléchargement en mémoire vive (bytes)
        # Cela évite les I/O inutiles sur le disque du Raspberry Pi
        audio_bytes = await telegram_file.download_as_bytearray()
        
        # 3. Création de l'objet "Part" pour l'API
        audio_part = types.Part.from_bytes(
            data=bytes(audio_bytes),
            mime_type=audio_attachment.mime_type or 'audio/ogg'
        )
        
        # 4. Appel asynchrone via le ROUTEUR
        router = get_gemini_router_service()
        prompt = "Transcris ce message vocal avec une précision absolue. Ne rajoute absolument aucun commentaire, renvoie UNIQUEMENT le texte prononcé."
        
        response = await router.generate_content(
            model_tier="flash",
            contents=[audio_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0 # Température à 0 pour éviter la moindre hallucination
            ),
            action_context="Transcription_Audio_Telegram"
        )
        
        return response.text.strip()


    def _purge_old_history(self, days: int = 7) -> None:
        """
        Filtre l'historique conversationnel pour ne conserver que les messages
        plus récents que le nombre de jours spécifié.
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # On recrée la liste en ne gardant que les éléments récents
        self.chat_history.turns = [
            turn for turn in self.chat_history.turns 
            if turn.timestamp >= cutoff_date
        ]

    def _save_history(self) -> None:
        """
        Sauvegarde de manière synchrone l'état actuel de la mémoire conversationnelle 
        dans un fichier JSON local, après avoir purgé les messages obsolètes.
        """
        try:
            # S'assurer que le dossier parent (ex: data/) existe
            self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Nettoyage de la mémoire glissante avant sauvegarde
            self._purge_old_history(days=get_settings().CHAT_HISTORY_DAYS)
            
            # Génération du JSON via Pydantic et écriture dans le fichier
            json_data = self.chat_history.model_dump_json(indent=2)
            self.history_file_path.write_text(json_data, encoding="utf-8")
            logger.debug("Historique conversationnel sauvegardé localement (et purgé).")
        except Exception as e:
            logger.error(f"Échec de la sauvegarde de l'historique conversationnel : {e}")