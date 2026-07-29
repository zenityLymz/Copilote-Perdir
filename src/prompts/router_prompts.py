def get_router_system_prompt() -> str:
    """
    Génère le prompt système pour l'Agent Routeur (Gemini Flash).
    
    Définit le rôle de l'assistant : agir comme un "standardiste" (aiguilleur) 
    qui analyse l'intention d'un message Telegram en langage naturel et 
    détermine la route métier correspondante parmi 5 choix stricts :
    1. 'agenda' (Rendez-vous, rappels, tâches)
    2. 'rag_search' (Recherche d'information dans l'historique)
    3. 'briefing' (Demande de résumé des e-mails)
    4. 'main_courante' (Déclaration d'un incident factuel)
    5. 'strategic_buffer' (Note de réflexion à mémoriser pour plus tard)
    
    Il impose également à l'IA de ne répondre qu'avec la clé exacte de la route.
    
    Returns:
        str: Le prompt système contenant les définitions des routes et les règles 
             de classification.
    """
    pass

def build_router_prompt(user_message: str) -> str:
    """
    Construit le prompt utilisateur pour soumettre le message à la classification.
    
    Args:
        user_message (str): Le message brut (texte ou transcription vocale) 
                            envoyé par le chef d'établissement sur Telegram.
                            
    Returns:
        str: Le prompt formaté intégrant le message à analyser pour l'Agent Routeur.
    """
    pass