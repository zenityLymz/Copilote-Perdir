"""
Registre des dépendances (Service Locator)

Ce module stocke les instances uniques (Singletons) des services 
nécessitant une connexion persistante (IMAP, Base de données, API Google).
Cela évite de recréer et reconnecter les services à chaque appel d'outil,
garantissant ainsi des performances optimales et le respect des limites des serveurs.
"""

from typing import Optional

# Typage pour l'autocomplétion (nous importerons les vraies classes au moment de l'utilisation)
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.google_drive_api import GoogleDriveService

# Stockage global des instances
_imap_service: Optional[IMAPService] = None
_chroma_service: Optional[ChromaDBService] = None
_drive_service: Optional[GoogleDriveService] = None

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