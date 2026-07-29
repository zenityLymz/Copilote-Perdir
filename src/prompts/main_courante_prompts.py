from typing import List, Optional
from src.core.models import MailObject

def get_main_courante_system_prompt() -> str:
    """
    Génère le prompt système pour l'Agent Main Courante (Gemini Flash).
    
    Définit le rôle de l'assistant : agir comme un secrétaire de direction
    chargé de consigner des faits de manière strictement neutre, factuelle, 
    professionnelle et horodatée. Impose le format de sortie en Markdown 
    et l'utilisation d'un système de balises/tags précis (ex: @Nom, #Incident) 
    pour faciliter la recherche ultérieure.
    
    Returns:
        str: Le prompt système au format texte avec les règles de rédaction.
    """
    pass

def build_main_courante_mail_prompt(mail: MailObject, existing_tags: Optional[List[str]] = None) -> str:
    """
    Construit le prompt utilisateur pour générer une entrée de main courante 
    à partir d'un e-mail (Pipeline A).
    
    Args:
        mail (MailObject): L'e-mail source contenant les faits à consigner.
        existing_tags (Optional[List[str]]): Les tags déjà présents dans le fichier 
                                             actuel, à réutiliser prioritairement pour 
                                             éviter les doublons (ex: éviter d'avoir 
                                             #Bagarre et #Altercation).
        
    Returns:
        str: Le prompt formaté contenant les instructions, le contexte des tags 
             et le contenu de l'e-mail.
    """
    pass

def build_main_courante_text_prompt(raw_text: str, existing_tags: Optional[List[str]] = None) -> str:
    """
    Construit le prompt utilisateur pour générer une entrée de main courante 
    à partir d'un compte-rendu dicté sur Telegram (Pipeline B).
    
    Args:
        raw_text (str): La description brute, textuelle ou vocale transcrite, 
                        fournie par le chef d'établissement.
        existing_tags (Optional[List[str]]): Les tags existants dans le document 
                                             pour harmoniser l'indexation.
        
    Returns:
        str: Le prompt formaté contenant le texte dicté et les consignes de formatage.
    """
    pass