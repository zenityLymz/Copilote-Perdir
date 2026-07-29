from typing import List, Optional
from google import genai

from src.core.models import MailObject
from src.core.config import get_settings
from src.utils.logger import get_logger

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class BriefingAgent:
    """
    Agent IA spécialisé dans la synthèse et le résumé d'e-mails (Route Briefing).
    Il agrège une liste d'e-mails (urgents ou non lus) et génère un rapport 
    structuré, concis et directement lisible sur Telegram.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour la génération de briefings.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser (Gemini Flash recommandé).
        """
        pass

    async def generate_briefing(self, emails: List[MailObject], user_instruction: Optional[str] = None) -> str:
        """
        Analyse une liste d'e-mails et génère un résumé structuré de manière asynchrone.
        Prend en compte les instructions spécifiques de l'utilisateur si fournies 
        (ex: "Fais-moi un point uniquement sur les urgences RH").

        Args:
            emails (List[MailObject]): La liste des e-mails extraits via l'IMAPService.
            user_instruction (Optional[str]): Une précision éventuelle donnée par 
                                              le chef d'établissement via Telegram.

        Returns:
            str: Le texte du briefing formaté en Markdown, prêt à être expédié sur Telegram.
        """
        pass