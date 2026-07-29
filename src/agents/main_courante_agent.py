from typing import List, Optional
from google import genai

from src.core.models import MailObject, EventLog
from src.core.config import get_settings
from src.utils.logger import get_logger

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class MainCouranteAgent:
    """
    Agent IA spécialisé dans la rédaction et le formatage des incidents 
    pour le journal de bord (Main Courante).
    Il intervient aussi bien de manière passive (Pipeline A - suite à un e-mail) 
    qu'active (Pipeline B - suite à un message Telegram).
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour la gestion de la main courante.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser (Gemini Flash recommandé).
        """
        pass

    async def format_from_mail(self, mail: MailObject, existing_tags: Optional[List[str]] = None) -> str:
        """
        Analyse un e-mail contenant un événement sensible et génère une entrée factuelle, 
        professionnelle et balisée pour la Main Courante.

        Args:
            mail (MailObject): L'objet e-mail source contenant l'incident.
            existing_tags (Optional[List[str]]): Liste des tags (noms, types d'incidents) déjà utilisés 
                                                 dans le document pour favoriser la cohérence et 
                                                 éviter les doublons.

        Returns:
            str: La nouvelle entrée formatée en Markdown, prête à être ajoutée 
                 au fichier Main_Courante.md (Append).
        """
        pass

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
        pass