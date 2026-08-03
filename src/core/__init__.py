"""
Module cœur (core)

Ce module centralise les fondations de l'application :
- Les modèles de données Pydantic (typage strict).
- La configuration globale (variables d'environnement).
- La hiérarchie des exceptions personnalisées.

Le fait de tout exposer ici permet au reste de l'application de faire des imports 
propres et concis (ex: `from src.core import MailObject, get_settings`).
"""

# --- Modèles de données ---
from .models import (
    DossierCible,
    TypeActionAgenda,
    MailObject,
    IA_TriResponse,
    TriDecision,
    AgendaTaskRequest,
    ConversationTurn,
    ChatHistory
)

# --- Dependencies (Service Locator) ---
from .dependencies import (
    get_imap_service,
    set_imap_service,
    get_chroma_service,
    set_chroma_service,
    get_drive_service,
    set_drive_service,
    get_telegram_service,
    set_telegram_service
)

# --- Configuration ---
from .config import (
    Settings, 
    get_settings
)

# --- Exceptions métiers ---
from .exceptions import (
    AssistantPerdirError,
    IMAPError,
    AgentError,
    GoogleAPIError,
    ChromaDBError,
    TelegramBotError,
    WorkflowError
)