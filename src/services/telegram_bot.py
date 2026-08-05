from typing import Callable, Any, Awaitable
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from telegram.constants import ParseMode

from src.utils.logger import get_logger
from src.core.config import get_settings
from src.core.exceptions import TelegramBotError

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class TelegramBotService:
    """
    Gère l'interface de communication mobile avec le chef d'établissement via l'API Telegram.
    Fonctionne en mode asynchrone et "Long Polling" pour s'intégrer de manière non-bloquante.
    """

    def __init__(self, token: str = None, allowed_user_id: str = None) -> None:
        """
        Initialise l'application du bot Telegram avec des restrictions de sécurité strictes.
        Récupère automatiquement les valeurs depuis config.py si elles ne sont pas fournies.

        Args:
            token (str, optional): Le jeton d'accès fourni par BotFather.
            allowed_user_id (str, optional): L'ID Telegram unique du chef d'établissement.
        """
        # Utilisation de la configuration centralisée
        settings = get_settings()
        self._token = token or settings.TELEGRAM_BOT_TOKEN
        self._allowed_user_id = str(allowed_user_id or settings.TELEGRAM_ALLOWED_USER_ID)
        
        try:
            # Construction de l'application (python-telegram-bot v20+)
            self.app = ApplicationBuilder().token(self._token).build()
            logger.info("Application Telegram initialisée avec succès.")
            
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'application Telegram: {e}")
            raise TelegramBotError(f"Échec de l'initialisation du bot : {e}")


    async def start_polling(self) -> None:
        """
        Démarre l'écoute active (Long Polling) des messages entrants de manière asynchrone.
        Permet au reste du programme de continuer à s'exécuter.
        """
        logger.info("Démarrage du bot Telegram en mode Long Polling...")
        try:
            # Initialisation asynchrone requise pour v20+ quand on gère la boucle manuellement
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            logger.info("Le bot Telegram est en cours d'exécution et écoute les messages.")
        except Exception as e:
            logger.error(f"Erreur fatale lors du démarrage du Long Polling: {e}")
            raise TelegramBotError(f"Impossible de démarrer le Long Polling : {e}")

    async def send_notification(self, message: str) -> bool:
        """
        Envoie une notification push ou une alerte au chef d'établissement.
        Utilisé notamment pour les e-mails classés "URGENT" par l'agent de triage.

        Args:
            message (str): Le contenu de l'alerte à envoyer.

        Returns:
            bool: True si l'envoi est un succès.
        """
        logger.debug("Tentative d'envoi d'une notification Telegram...")
        try:
            # On utilise bot.send_message pour envoyer directement à l'ID autorisé
            await self.app.bot.send_message(chat_id=self._allowed_user_id, text=message, parse_mode=ParseMode.HTML)
            logger.info("Notification Telegram envoyée avec succès.")
            return True
        except TelegramError as e:
            logger.error(f"Échec de l'envoi de la notification Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'envoi de la notification: {e}")
            return False

    def register_command(self, command: str, handler_func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]) -> None:
        """
        Associe une commande texte (ex: /briefing, /recherche) à une fonction métier spécifique (coroutine).

        Args:
            command (str): Le nom de la commande (sans le '/').
            handler_func (Callable): La coroutine asynchrone à exécuter.
        """
        # On wrap la fonction pour garantir que seul l'utilisateur autorisé peut l'exécuter
        async def secure_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if str(update.effective_user.id) != self._allowed_user_id:
                logger.warning(f"Tentative d'exécution de /{command} par un utilisateur non autorisé ({update.effective_user.id}).")
                return
            
            logger.info(f"Exécution de la commande /{command} par le chef d'établissement.")
            await handler_func(update, context)

        self.app.add_handler(CommandHandler(command, secure_handler))
        logger.info(f"Commande métier dynamique '/{command}' enregistrée avec succès.")


    def register_message_handler(self, handler_func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]) -> None:
        """
        Enregistre un gestionnaire global pour intercepter les messages en langage naturel 
        (texte) et les notes vocales du chef d'établissement.
        Ignore automatiquement les commandes (commençant par '/') pour éviter les conflits.

        Args:
            handler_func (Callable): La coroutine asynchrone métier à exécuter 
                                     (doit accepter Update et ContextTypes).
        """
        # Fermeture de sécurité (Closure) identique à register_command
        async def secure_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

            # Si update.message est None (ce qui arrive lors d'une édition), on ignore silencieusement.
            # Cela évite que l'IA ne traite deux fois la même commande.
            if not update.message:
                return

            # Vérification de l'identité de l'expéditeur
            # Le bot accepte si moi 
            if str(update.effective_user.id) != self._allowed_user_id :
                logger.warning(
                    f"Tentative de message interceptée d'un utilisateur non autorisé "
                    f"({update.effective_user.id})."
                )
                return
            
            # Log de l'activité (utile pour le débogage de l'IA)
            msg_type = "vocal" if update.message.voice else "texte"
            logger.info(f"Réception d'un message {msg_type} libre de la part du chef d'établissement.")
            
            # Transfert au workflow métier (qui appellera Gemini / ChromaDB)
            await handler_func(update, context)

        # Création du filtre : (Texte OU Vocal) ET (PAS une commande)
        custom_filter = (filters.TEXT | filters.VOICE) & ~filters.COMMAND
        
        # Ajout du gestionnaire à l'application
        self.app.add_handler(MessageHandler(custom_filter, secure_message_handler))
        logger.info("Gestionnaire de messages (texte et vocal) enregistré avec succès.")