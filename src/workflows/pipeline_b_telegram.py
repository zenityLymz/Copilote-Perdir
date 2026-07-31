from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.utils.logger import get_logger
from src.agents.orchestrator_agent import OrchestratorAgent
from src.services.telegram_bot import TelegramBotService
from src.core.models import ChatHistory

# Initialisation du logger
logger = get_logger(__name__)

class PipelineBTelegram:
    """
    Orchestrateur du Pipeline B (Actif) : Assistant Interactif Telegram.
    
    Ce workflow est déclenché par la réception d'un message (texte ou audio) 
    du chef d'établissement. Il maintient l'état de la conversation (ChatHistory) 
    pour conserver le contexte et délègue le raisonnement et l'action 
    à l'OrchestratorAgent.
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
        
        # Instanciation de la mémoire locale de la conversation
        self.chat_history = ChatHistory()
        
        logger.debug("Pipeline B (Telegram) initialisé avec ses dépendances et sa mémoire locale.")

    async def process_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Point d'entrée asynchrone interceptant les messages Telegram du Perdir.
        S'occupe d'extraire le texte (ou transcrire le vocal), de mettre à jour 
        la mémoire, d'interroger l'Orchestrateur et de renvoyer la réponse.

        Args:
            update (Update): L'objet natif Telegram contenant le message.
            context (ContextTypes.DEFAULT_TYPE): Le contexte d'exécution de python-telegram-bot.
        """
        # TODO: Extraire le message texte (ou transcrire l'audio) depuis l'objet 'update'.
        
        # TODO: Mettre à jour self.chat_history (ajouter le tour de parole de l'utilisateur).
        
        # TODO: Appeler self.orchestrator_agent.process_user_request(texte_utilisateur, self.chat_history).
        
        # TODO: Mettre à jour self.chat_history (ajouter la réponse générée par l'IA).
        
        # TODO: Renvoyer la réponse de l'IA au chef d'établissement via self.telegram_service.
        pass