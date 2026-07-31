from typing import List, Optional
from google import genai
from google.genai import types

from src.core.models import MailObject
from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.utils.logger import get_logger

# Importation des constructeurs de prompts que nous venons de créer
from src.prompts.briefing_prompts import (
    get_briefing_system_prompt,
    build_briefing_prompt
)

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class BriefingAgent:
    """
    Agent IA spécialisé dans la synthèse et le résumé d'e-mails.
    Il agrège une liste d'e-mails et génère un rapport 
    structuré, concis et directement lisible sur Telegram.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour la génération de briefings.
        """
        try:
            settings = get_settings()
            self.client = genai.Client(api_key=api_key)
            # Utilisation de Gemini Flash par défaut : il est ultra-rapide 
            # et largement assez intelligent pour de la synthèse de texte.
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL
            
            logger.debug(f"BriefingAgent initialisé avec succès (Modèle: {self.model_name}).")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini (Briefing) : {e}")
            raise AgentError(f"Impossible d'initialiser l'Agent de Briefing : {e}")

    async def generate_briefing(self, emails: List[MailObject], user_instruction: Optional[str] = None) -> str:
        """
        Analyse une liste d'e-mails et génère un résumé structuré de manière asynchrone.
        """
        if not emails:
            return "Aucun e-mail à résumer."

        logger.info(f"Début de la génération du briefing pour {len(emails)} e-mails. (Critère : {user_instruction or 'Aucun'})")
        
        try:
            # 1. Préparation des prompts
            system_prompt = get_briefing_system_prompt()
            user_prompt = build_briefing_prompt(emails, user_instruction)

            # 2. Appel asynchrone à l'API Gemini
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Température basse (0.2) : On veut de la précision factuelle, pas de l'invention littéraire
                    temperature=0.2, 
                )
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini (BriefingAgent) est vide.")

            logger.info("Briefing généré avec succès.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec de la génération du briefing : {e}", exc_info=True)
            raise AgentError(f"Erreur lors de l'appel à l'API Gemini (Briefing) : {e}")