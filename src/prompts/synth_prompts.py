def get_pilotage_system_prompt() -> str:
    """
    Génère le prompt système pour l'agent de synthèse (Gemini Pro).
    
    Définit le rôle de l'assistant : agir comme un conseiller stratégique capable 
    de prendre du recul sur les événements d'une journée. Il doit lire un flux 
    d'informations hétérogènes, identifier ce qui relève du structurel/macroscopique 
    (Bâti, RH, Finances, Climat), et l'intégrer intelligemment dans un document 
    Markdown sans en casser l'arborescence.
    
    Returns:
        str: Le prompt système imposant les règles strictes de fusion de contenu.
    """
    pass

def build_pilotage_update_prompt(current_content: str, daily_info: str) -> str:
    """
    Construit le prompt pour la mécanique de mise à jour ("Read-Rewrite-Replace").
    Demande à l'agent d'évaluer l'impact de `daily_info` sur `current_content` 
    et de générer la nouvelle version intégrale du document.
    
    Args:
        current_content (str): Le contenu Markdown brut du fichier central de pilotage.
        daily_info (str): La concaténation des e-mails et notes Telegram de la journée.
        
    Returns:
        str: Le prompt contenant les instructions de fusion et les données à traiter.
    """
    pass

def build_summary_prompt(changes_diff: str) -> str:
    """
    Construit un prompt demandant à l'IA de résumer de manière très concise 
    les modifications qu'elle vient d'apporter au fichier de pilotage (pour Telegram).
    
    Args:
        changes_diff (str): Les éléments modifiés ou le delta entre les deux versions.
        
    Returns:
        str: Le prompt demandant la création d'un court message de notification.
    """
    pass