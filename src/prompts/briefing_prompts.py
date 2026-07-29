from typing import List, Optional
from src.core.models import MailObject

def get_briefing_system_prompt() -> str:
    """
    Génère le prompt système pour l'agent de briefing (Gemini Flash).
    
    Définit le rôle de l'assistant : résumer de manière ultra-concise, professionnelle
    et structurée une liste d'e-mails pour une lecture rapide sur un écran de 
    smartphone (via Telegram). Le prompt doit imposer l'utilisation de listes à puces 
    et d'émojis pertinents, tout en évitant les détails superflus.
    
    Returns:
        str: Le prompt système contenant les règles strictes de synthèse et de formatage.
    """
    pass

def build_briefing_prompt(emails: List[MailObject], user_instruction: Optional[str] = None) -> str:
    """
    Construit le prompt utilisateur en agrégeant les métadonnées et le contenu 
    des e-mails à résumer, tout en intégrant les instructions spécifiques éventuelles.
    
    Args:
        emails (List[MailObject]): La liste des e-mails (récupérés via IMAP) à synthétiser.
        user_instruction (Optional[str]): Une instruction spécifique dictée par le 
                                          chef d'établissement (ex: "Fais un point 
                                          uniquement sur les urgences RH").
                                          
    Returns:
        str: Le prompt texte complet, formaté pour être injecté dans la requête au modèle.
    """
    pass