from typing import Optional, Tuple, List
from google import genai
from google.genai import types
from pydantic import ValidationError

from src.core.models import IA_RouterResponse, RouteChoice
from src.core.exceptions import AgentError
from src.core.config import get_settings
from src.prompts.router_prompts import get_router_system_prompt, build_router_prompt
from src.utils.logger import get_logger

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class RouterAgent:
    """
    Agent IA agissant comme le 'standardiste' de l'application (Pipeline B).
    Son rôle exclusif est d'analyser un message en langage naturel (texte ou 
    transcription vocale) en provenance de Telegram et de déterminer la route 
    métier la plus appropriée.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour la classification d'intentions.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser (Gemini Flash recommandé 
                                        pour la rapidité de classification).
        """
        try:
            # Récupération de la configuration globale
            settings = get_settings()

            # Initialisation du nouveau client SDK Google GenAI
            self.client = genai.Client(api_key=api_key)

            # Si aucun modèle n'est fourni, on prend celui du config.py (Flash par défaut)
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL
            
            logger.debug(f"RouterAgent initialisé avec succès (Modèle: {self.model_name}).")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini : {e}")
            raise AgentError(f"Impossible d'initialiser l'agent routeur : {e}")

    async def classify_intent(self, user_message: str) -> Tuple[List[RouteChoice], Optional[str]]:
        """
        Analyse le message et retourne une liste de routes et une explication éventuelle.

        Returns:
            Tuple[List[RouteChoice], Optional[str]]: La liste des routes (ex: ['agenda', 'main_courante']) 
                                             et l'explication si la route 'autre_ou_incomplet' est présente.
        """
        try:
            logger.debug(f"Demande de classification d'intention...")
            
            system_prompt = get_router_system_prompt()
            user_prompt = build_router_prompt(user_message)

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=IA_RouterResponse,
                    temperature=0.0
                )
            )

            ia_response = IA_RouterResponse.model_validate_json(response.text)
            
            routes = ia_response.routes_choisies
            
            logger.info(f"Intention(s) classifiée(s) : {[r.value for r in routes]}")
            
            return routes, ia_response.explication

        except ValidationError as e:
            logger.error(f"Erreur de validation Pydantic de la réponse IA pour le message : {e}")
            raise AgentError(f"Le format renvoyé par l'IA ne correspond pas à IA_RouterResponse : {e}")
            
        except Exception as e:
            logger.error(f"Échec de l'évaluation asynchrone de l'intention par l'IA : {e}")
            raise AgentError(f"Erreur lors de l'appel à l'API Gemini : {e}")