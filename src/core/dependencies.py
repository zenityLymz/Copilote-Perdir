"""
Registre des dépendances (Service Locator)

Ce module stocke les instances uniques (Singletons) des services 
nécessitant une connexion persistante (IMAP, Base de données, API Google).
Cela évite de recréer et reconnecter les services à chaque appel d'outil,
garantissant ainsi des performances optimales et le respect des limites des serveurs.
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

# TYPE_CHECKING est Vrai pour l'éditeur de code (VS Code), 
# mais Faux quand le programme s'exécute, ce qui évite l'import circulaire !
if TYPE_CHECKING:
    from src.services.imap_service import IMAPService
    from src.services.chroma_service import ChromaDBService
    from src.services.google_drive_api import GoogleDriveService
    from src.services.telegram_bot import TelegramBotService

# L'astuce est de mettre le nom du type entre guillemets ('IMAPService') 
# car la classe n'est pas "réellement" importée à l'exécution.
_imap_service: Optional['IMAPService'] = None
_chroma_service: Optional['ChromaDBService'] = None
_drive_service: Optional['GoogleDriveService'] = None
_telegram_service: Optional['TelegramBotService'] = None

# --- Service IMAP ---
def get_imap_service() -> IMAPService:
    if _imap_service is None:
        raise RuntimeError("Le service IMAP n'a pas été initialisé dans le registre.")
    return _imap_service

def set_imap_service(service: IMAPService) -> None:
    global _imap_service
    _imap_service = service

# --- Service ChromaDB (Base vectorielle) ---
def get_chroma_service() -> ChromaDBService:
    if _chroma_service is None:
        raise RuntimeError("Le service ChromaDB n'a pas été initialisé dans le registre.")
    return _chroma_service

def set_chroma_service(service: ChromaDBService) -> None:
    global _chroma_service
    _chroma_service = service

# --- Service Google Drive ---
def get_drive_service() -> GoogleDriveService:
    if _drive_service is None:
        raise RuntimeError("Le service Google Drive n'a pas été initialisé dans le registre.")
    return _drive_service

def set_drive_service(service: GoogleDriveService) -> None:
    global _drive_service
    _drive_service = service

# --- Service Telegram ---
def get_telegram_service() -> TelegramBotService:
    if _telegram_service is None:
        raise RuntimeError("Le service Telegram n'a pas été initialisé dans le registre.")
    return _telegram_service

def set_telegram_service(service: TelegramBotService) -> None:
    global _telegram_service
    _telegram_service = service