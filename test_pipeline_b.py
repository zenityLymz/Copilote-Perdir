import asyncio
import logging
from dotenv import load_dotenv

from src.utils.logger import setup_logger, get_logger
from src.core.config import get_settings
from src.agents.orchestrator_agent import OrchestratorAgent
from src.services.telegram_bot import TelegramBotService
from src.workflows.pipeline_b_telegram import PipelineBTelegram

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
        
        # 3. Instanciation des Services et Agents nécessaires
        logger.info("Initialisation de l'Agent Orchestrateur...")
        orchestrator = OrchestratorAgent(api_key=settings.GEMINI_API_KEY)
        
        logger.info("Initialisation du Service Telegram...")
        telegram_service = TelegramBotService()
        
        # 4. Instanciation du Pipeline (Le Chef d'Orchestre)
        logger.info("Câblage du Pipeline B...")
        pipeline_b = PipelineBTelegram(
            telegram_service=telegram_service,
            orchestrator_agent=orchestrator
        )
        
        # 5. Enregistrement du gestionnaire de messages
        # On dit au service Telegram : "Quand tu reçois un message, donne-le au Pipeline B"
        telegram_service.register_message_handler(pipeline_b.process_telegram_message)
        
        # 6. Démarrage de l'écoute sur Telegram (Long Polling)
        logger.info("🚀 Le bot est prêt ! Vous pouvez lui envoyer un message sur Telegram.")
        await telegram_service.start_polling()
        
        # Pour maintenir le script en vie indéfiniment pendant que le bot écoute
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"Erreur critique lors du test : {e}", exc_info=True)

if __name__ == "__main__":
    # Lancement de la boucle asynchrone principale
    asyncio.run(main())