from typing import Callable, Any, Awaitable
from telegram import Update
from telegram.ext import ContextTypes

class TelegramBotService:
    """
    Gère l'interface de communication mobile avec le chef d'établissement via l'API Telegram.
    Fonctionne en mode asynchrone et "Long Polling" pour s'intégrer de manière non-bloquante.
    """

    def __init__(self, token: str, allowed_user_id: str) -> None:
        """
        Initialise l'application du bot Telegram avec des restrictions de sécurité strictes.

        Args:
            token (str): Le jeton d'accès fourni par BotFather (stocké dans .env).
            allowed_user_id (str): L'ID Telegram unique du chef d'établissement pour sécuriser l'accès.
        """
        pass

    async def start_polling(self) -> None:
        """
        Démarre l'écoute active (Long Polling) des messages entrants de manière asynchrone.
        Permet au reste du programme de continuer à s'exécuter.
        """
        pass

    async def send_notification(self, message: str) -> bool:
        """
        Envoie une notification push ou une alerte au chef d'établissement.
        Utilisé notamment pour les e-mails classés "URGENT" par l'agent de triage.

        Args:
            message (str): Le contenu de l'alerte à envoyer.

        Returns:
            bool: True si l'envoi est un succès.
        """
        pass

    def register_command(self, command: str, handler_func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]) -> None:
        """
        Associe une commande texte (ex: /briefing, /recherche) à une fonction métier spécifique (coroutine).

        Args:
            command (str): Le nom de la commande (sans le '/').
            handler_func (Callable): La coroutine asynchrone à exécuter (doit accepter Update et ContextTypes).
        """
        pass