from typing import List, Optional
from google import genai
from google.genai import types

from src.core.models import MailObject
from src.core.exceptions import AgentError
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service

# Importation des constructeurs de prompts depuis le module dédié
from src.prompts.main_courante_prompts import (
    get_main_courante_system_prompt,
    build_main_courante_text_prompt
)

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class MainCouranteAgent:
    """
    Agent IA spécialisé dans la rédaction et le formatage des incidents 
    pour le journal de bord (Main Courante).
    Il intervient à la demande du chef d'établissement via le pipeline Telegram.
    """

    def __init__(self) -> None:
        """
        Initialise le client de l'API Gemini pour la gestion de la main courante.

        """
        try:
            self.router = get_gemini_router_service()
            logger.debug(f"MainCouranteAgent initialisé avec succès via GeminiRouterService.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini : {e}")
            raise AgentError(f"Impossible d'initialiser l'Agent Main Courante : {e}")


    async def format_from_text(self, raw_text: str, existing_tags: Optional[List[str]] = None) -> str:
        """
        Prend un compte-rendu brut dicté par le chef d'établissement via Telegram 
        et le reformate en un rapport d'incident neutre, factuel et structuré.

        Args:
            raw_text (str): Le texte brut ou la transcription vocale du Perdir.
            existing_tags (Optional[List[str]]): Liste des balises existantes pour harmoniser 
                                                 l'indexation.

        Returns:
            str: La nouvelle entrée formatée en Markdown, prête à être concaténée 
                 au fichier de suivi.
        """
        logger.debug("Génération d'une entrée Main Courante à partir d'un texte dicté/Telegram.")
        try:
            # Récupération des prompts
            system_prompt = get_main_courante_system_prompt()
            user_prompt = build_main_courante_text_prompt(raw_text, existing_tags)

            # Appel asynchrone à l'API Gemini
            response = await self.router.generate_content(
                model_tier="flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Toujours une température très basse pour garantir le ton "Secrétariat de Direction"
                    temperature=0.1,
                ),
                action_context="MainCourante_Texte"
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini est vide.")

            logger.info("Entrée Main Courante générée avec succès depuis le texte brut.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec du formatage Main Courante depuis le texte Telegram : {e}")
            raise AgentError(f"Erreur lors du formatage Main Courante depuis un texte : {e}")