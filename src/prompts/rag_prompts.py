from typing import List

def get_rag_system_prompt() -> str:
    """
    Génère le prompt système définissant les règles de réponse de l'agent RAG[cite: 42].
    Impose au modèle de ne répondre qu'avec le contexte fourni pour éviter 
    les hallucinations.
    
    Returns:
        str: Le prompt système strict pour le RAG.
    """
    pass

def build_rag_qa_prompt(user_query: str, retrieved_context: List[str]) -> str:
    """
    Construit le prompt de question-réponse combinant la demande de l'utilisateur
    et le contexte pertinent retrouvé par sémantique dans ChromaDB.
    
    Args:
        user_query (str): La requête en langage naturel du chef d'établissement.
        retrieved_context (List[str]): Les fragments de texte extraits de la base locale.
        
    Returns:
        str: Le prompt formaté intégrant la question et le contexte d'appui.
    """
    pass