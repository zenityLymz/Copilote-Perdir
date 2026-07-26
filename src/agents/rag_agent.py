from typing import List, Dict, Any

class RAGAgent:
    """
    Agent IA spécialisé dans la génération de réponses augmentées par la recherche (RAG).
    Il prend une question en langage naturel et les documents pertinents issus 
    de la base vectorielle ChromaDB pour formuler une réponse précise.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        """
        Initialise le client de l'API Gemini pour la synthèse documentaire.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (str): Le modèle à utiliser.
        """
        pass

    def generate_answer(self, query: str, retrieved_context: List[Dict[str, Any]]) -> str:
        """
        Génère une réponse à la question de l'utilisateur en se basant *uniquement* sur le contexte fourni (e-mails ou documents retrouvés).

        Args:
            query (str): La question posée par le chef d'établissement via Telegram.
            retrieved_context (List[Dict[str, Any]]): Les documents extraits de ChromaDB 
                                                      avec leurs métadonnées.

        Returns:
            str: La réponse formatée, prête à être envoyée sur Telegram.
        """
        pass