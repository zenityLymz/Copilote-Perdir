from src.core.models import MailObject

def get_triage_system_prompt() -> str:
    """
    Génère le prompt système global pour l'agent de triage (Gemini Flash)[cite: 42].
    Contient les règles d'évaluation (niveaux de priorité, dossiers cibles) et 
    force la sortie structurée selon le modèle TriDecision.
    
    Returns:
        str: Le prompt système au format texte.
    """
    pass

def build_mail_evaluation_prompt(mail: MailObject) -> str:
    """
    Construit le prompt utilisateur pour l'analyse d'un e-mail spécifique afin 
    de générer une décision de tri.
    
    Args:
        mail (MailObject): L'objet représentant l'e-mail entrant.
        
    Returns:
        str: Le prompt formaté contenant le corps et les métadonnées de l'e-mail.
    """
    pass