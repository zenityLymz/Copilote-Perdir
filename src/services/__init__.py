"""
Module des services (services)

Ce module centralise toutes les interactions avec des systèmes externes :
- Messagerie académique (IMAP)
- Base de données vectorielle locale (ChromaDB)
- API Google Workspace (Drive, Docs, Tasks, Calendar via OAuth 2.0)
- Bot Telegram (via Long Polling)
"""

from .imap_service import IMAPService
from .telegram_bot import TelegramBotService
from .chroma_service import ChromaDBService
from .google_drive_api import GoogleDriveService
from .google_calendar_tasks import GoogleCalendarTasksService
from .token_tracker import TokenTrackerService
from .gemini_router import GeminiRouterService