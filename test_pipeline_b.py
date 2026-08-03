import asyncio
import logging
from dotenv import load_dotenv
import os

from src.utils.logger import setup_logger, get_logger
from src.core.config import get_settings
from src.agents.orchestrator_agent import OrchestratorAgent
from src.services.telegram_bot import TelegramBotService
from src.workflows.pipeline_b_telegram import PipelineBTelegram

# Import du service IMAP et du registre
from src.services.imap_service import IMAPService
from src.core.dependencies import set_imap_service, get_imap_service

from src.services.chroma_service import ChromaDBService
from src.core.dependencies import set_chroma_service

from src.services.google_drive_api import GoogleDriveService
from src.core.dependencies import set_drive_service

from src.core.dependencies import set_telegram_service

# 1. Chargement explicite des variables d'environnement depuis le fichier .env
load_dotenv()

# 2. Configuration du logger pour le test (affichage dans la console)
setup_logger(log_level=logging.INFO)
logger = get_logger("TestPipelineB")

async def main():
    logger.info("=== DÉMARRAGE DU TEST DU PIPELINE B (Copilote IA) ===")
    
    try:
        # Récupération de la configuration (vérifie que le .env est bien rempli)
        settings = get_settings()
        
        # --- Connexion et enregistrement des services ---
        logger.info("Connexion au serveur IMAP...")
        imap_service = IMAPService()
        await imap_service.connect()
        set_imap_service(imap_service) # On le place dans le registre
        logger.info("IMAP connecté et enregistré dans le registre mondial.")
        
        
        logger.info("Initialisation de la base de données vectorielle (ChromaDB)...")
        
        # On définit le chemin du dossier de stockage et on le crée s'il n'existe pas
        chroma_dir = "./data/chroma_db"
        os.makedirs(chroma_dir, exist_ok=True)
        
        # On instancie le service en lui passant le chemin requis
        chroma_service = ChromaDBService(persist_directory=chroma_dir)
        set_chroma_service(chroma_service)
        
        logger.info("ChromaDB enregistré dans le registre mondial.")

        # --- Initialisation de Google Drive ---
        logger.info("Authentification au service Google Drive...")
        drive_service = GoogleDriveService()
        await drive_service.authenticate()
        set_drive_service(drive_service)
        logger.info("Google Drive authentifié et enregistré dans le registre mondial.")
        
        # 3. Instanciation des Services et Agents nécessaires
        logger.info("Initialisation de l'Agent Orchestrateur...")
        orchestrator = OrchestratorAgent(api_key=settings.GEMINI_API_KEY)
        
        logger.info("Initialisation du Service Telegram...")
        telegram_service = TelegramBotService()
        set_telegram_service(telegram_service)  # On l'enregistre dans le registre mondial
        
        # 4. Instanciation du Pipeline (Le Chef d'Orchestre)
        logger.info("Câblage du Pipeline B...")
        pipeline_b = PipelineBTelegram(
            telegram_service=telegram_service,
            orchestrator_agent=orchestrator
        )
        
        # 5. Enregistrement du gestionnaire de messages
        telegram_service.register_message_handler(pipeline_b.process_telegram_message)
        
        # 6. Démarrage de l'écoute sur Telegram
        logger.info("🚀 Le bot est prêt ! Vous pouvez lui envoyer un message sur Telegram.")
        await telegram_service.start_polling()
        
        # Pour maintenir le script en vie
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"Erreur critique lors du test : {e}", exc_info=True)
    finally:
        # Déconnexion propre de l'IMAP à l'arrêt du programme
        try:
            imap_service = get_imap_service()
            await imap_service.disconnect()
            logger.info("Service IMAP déconnecté proprement.")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())