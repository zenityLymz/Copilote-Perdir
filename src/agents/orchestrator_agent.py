from typing import Optional, List, Dict, Any, Callable
from google import genai

from src.core.models import ChatHistory
from src.core.config import get_settings
from src.utils.logger import get_logger

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class OrchestratorAgent:
    """
    Agent central et autonome du Pipeline B (Agentic Loop).
    Remplace l'ancien RouterAgent statique. Il gère la mémoire conversationnelle, 
    raisonne sur l'intention de l'utilisateur, et invoque dynamiquement des outils 
    (Function Calling) si des actions sont nécessaires.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour l'orchestrateur.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser.
        """
        pass

    async def process_user_request(self, user_message: str, chat_history: ChatHistory) -> str:
        """
        Traite une nouvelle demande du chef d'établissement.
        L'agent analyse le contexte, vérifie s'il doit interroger l'utilisateur 
        pour des paramètres manquants, ou déclenche ses outils de façon autonome.

        Args:
            user_message (str): Le message texte (ou transcription audio) de l'utilisateur.
            chat_history (ChatHistory): L'historique des échanges pour le maintien du contexte.

        Returns:
            str: La réponse finale et naturelle formulée par l'IA.
        """
        pass

    def _get_available_tools(self) -> List[Callable]:
        """
        Définit et retourne la liste des fonctions (outils) Python mises 
        à la disposition de l'agent (ex: ajouter_main_courante, rechercher_document_drive, etc.).
        
        Returns:
            List[Callable]: Les références aux fonctions utilisables via le Function Calling du SDK genai.
        """
        pass