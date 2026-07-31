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