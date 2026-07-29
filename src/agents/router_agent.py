from typing import Optional
from google import genai

from src.core.config import get_settings
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
        pass

    async def classify_intent(self, user_message: str) -> str:
        """
        Analyse le message de l'utilisateur et retourne l'identifiant de la route à suivre.
        Utilise de préférence le 'Structured Output' de Gemini pour contraindre le LLM 
        à ne répondre qu'avec une des valeurs de routage autorisées.

        Les routes possibles correspondent aux 5 actions du Pipeline B[cite: 24, 26, 28, 30, 32]:
        - "agenda" (Création de tâche/événement)
        - "rag_search" (Interrogation de la base de connaissances)
        - "briefing" (Demande de synthèse d'e-mails)
        - "main_courante" (Déclaration d'un incident)
        - "strategic_buffer" (Information à mémoriser pour le soir)

        Args:
            user_message (str): Le message brut (ou transcrit) reçu sur Telegram.

        Returns:
            str: L'identifiant textuel (ou une Enum si définie dans le core) de la route sélectionnée par l'IA.
        """
        pass