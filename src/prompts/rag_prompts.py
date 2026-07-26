from typing import List

class RAGPromptManager:
    """
    Gestionnaire des prompts destinés à un agent d'extraction RAG[cite: 42].
    Spécialisé dans la structuration des réponses basées sur la base vectorielle.
    """

    @staticmethod
    def get_system_prompt() -> str:
        """
        Génère le prompt système définissant les règles de réponse (pas d'hallucination,
        citation des sources obligatoires).
        
        Returns:
            str: Le prompt système strict pour le RAG.
        """
        pass

    @staticmethod
    def build_qa_prompt(user_query: str, retrieved_context: List[str]) -> str:
        """
        Construit le prompt de question-réponse combinant la demande de l'utilisateur
        et le contexte pertinent retrouvé par sémantique.
        
        Args:
            user_query (str): La requête en langage naturel de l'utilisateur.
            retrieved_context (List[str]): Les fragments de texte extraits de la base locale.
            
        Returns:
            str: Le prompt formaté intégrant le contexte d'appui.
        """
        pass