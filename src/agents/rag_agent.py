from typing import List, Dict, Any, Optional
from google import genai

from src.core.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RAGAgent:
    """
    Agent IA spécialisé dans la génération de réponses augmentées par la recherche (RAG).
    Il prend une question en langage naturel et les documents pertinents issus 
    de la base vectorielle ChromaDB pour formuler une réponse précise.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        pass

    async def generate_answer(self, query: str, retrieved_context: List[Dict[str, Any]]) -> str:
        """
        Génère une réponse à la question de l'utilisateur en se basant *uniquement* sur le contexte fourni de manière asynchrone.
        """
        pass