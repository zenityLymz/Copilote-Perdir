import os
from pathlib import Path
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.utils import get_logger
from src.agents import OrchestratorAgent
from src.services import TelegramBotService
from src.core import ChatHistory, ConversationTurn
from src.utils import split_telegram_message

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

    def _save_history(self) -> None:
        """
        Sauvegarde de manière synchrone l'état actuel de la mémoire conversationnelle 
        dans un fichier JSON local.
        """
        try:
            # S'assurer que le dossier parent (ex: data/) existe
            self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Génération du JSON via Pydantic et écriture dans le fichier
            json_data = self.chat_history.model_dump_json(indent=2)
            self.history_file_path.write_text(json_data, encoding="utf-8")
            logger.debug("Historique conversationnel sauvegardé localement.")
        except Exception as e:
            logger.error(f"Échec de la sauvegarde de l'historique conversationnel : {e}")

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
            # TODO : Télécharger le fichier audio/vocal via l'API Telegram en byte array.
            # TODO : Utiliser le SDK google-genai pour uploader l'audio (ou le passer en Base64/Inline) 
            # et générer la transcription textuelle de la requête du Perdir.
            logger.info("Message vocal reçu. Transcription différée en attente d'implémentation.")
            await update.message.reply_text("🗣️ Mémo vocal bien reçu ! La transcription automatique via Gemini arrivera dans une prochaine mise à jour.")
            return
        else:
            logger.warning("Format de message non supporté.")
            await update.message.reply_text("Désolé, je ne peux traiter que du texte ou des mémos vocaux.")
            return

        logger.debug(f"Requête utilisateur extraite : {user_text}")

        # 2. Mettre à jour la mémoire et sauvegarder
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
            self.chat_history.turns.append(
                ConversationTurn(role="model", message=ai_response)
            )
            self._save_history()
            
            # 5. Renvoyer la réponse de l'IA au chef d'établissement
            # Utilisation de text_utils pour éviter de crasher sur la limite de caractères Telegram (4096)
            response_chunks = split_telegram_message(ai_response)
            for chunk in response_chunks:
                await update.message.reply_text(chunk)
                
        except Exception as e:
            logger.error(f"Erreur critique lors du traitement du message par l'Orchestrateur : {e}", exc_info=True)
            await update.message.reply_text("⚠️ Désolé, une erreur technique m'a empêché de traiter votre demande. Veuillez réessayer.")