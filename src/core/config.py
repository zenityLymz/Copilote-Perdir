from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    Classe de configuration centrale de l'application.
    Valide et charge automatiquement les variables d'environnement depuis le fichier .env.
    Lève une erreur explicite au démarrage si une variable obligatoire est manquante.
    """

    # --- Configuration IMAP (Messagerie Académique) ---
    IMAP_HOST: str
    IMAP_USER: str
    IMAP_PASSWORD: str
    IMAP_PORT: int = 993

    # --- Configuration Telegram ---
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ALLOWED_USER_ID: str

    # --- Configuration Gemini IA ---
    GEMINI_API_KEY_FREE: str      # Clé liée au projet Google Cloud SANS carte bancaire
    GEMINI_API_KEY_PAID: str      # Clé liée au projet Google Cloud AVEC facturation
    GEMINI_FLASH_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_PRO_MODEL: str = "gemini-3.5-pro"

    # --- Tarification Gemini (Prix pour 1 Million de tokens en USD) ---
    PRICE_PRO_INPUT: float = 1.25
    PRICE_PRO_OUTPUT: float = 5.00
    PRICE_FLASH_INPUT: float = 0.075
    PRICE_FLASH_OUTPUT: float = 0.30

    # --- Configuration Google API ---
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    GOOGLE_TOKEN_PATH: str = "token.json"

    # --- Fichiers Drive (Markdown) ---
    MEMOIRE_FILE_ID: str
    MAIN_COURANTE_FILE_ID: str

    # --- Configuration ChromaDB ---
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"

    # --- Temps de pause entre les appels à l'API Gemini pour éviter le throttling ---
    GEMINI_API_PAUSE_SECONDS: float = 10.0

    # --- Nombre de jours de mémoire à conserver pour le contexte conversationnel ---
    CHAT_HISTORY_DAYS: int = 7

    # Comportement de Pydantic pour lire le fichier .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """
    Instancie et retourne les paramètres de configuration globaux.
    Fonctionne comme un singleton ou un injecteur de dépendances pour le reste de l'application.

    Returns:
        Settings: L'objet contenant toutes les variables de configuration typées et validées.
    """
    return Settings()