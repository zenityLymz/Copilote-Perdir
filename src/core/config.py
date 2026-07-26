from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    GEMINI_API_KEY: str
    GEMINI_FLASH_MODEL: str = "gemini-1.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-1.5-pro"

    # --- Configuration Google API ---
    GOOGLE_CREDENTIALS_PATH: str = "credentials.json"
    GOOGLE_TOKEN_PATH: str = "token.json"

    # --- Fichiers Drive (Markdown) ---
    PILOTAGE_FILE_ID: str
    MAIN_COURANTE_FILE_ID: str

    # --- Configuration ChromaDB ---
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    EMBEDDING_MODEL_NAME: str = "models/text-embedding-004"

    # Comportement de Pydantic pour lire le fichier .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def get_settings() -> Settings:
    """
    Instancie et retourne les paramètres de configuration globaux.
    Fonctionne comme un singleton ou un injecteur de dépendances pour le reste de l'application.

    Returns:
        Settings: L'objet contenant toutes les variables de configuration typées et validées.
    """
    pass