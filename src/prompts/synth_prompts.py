from typing import List
from src.core.models import MailObject, PilotageInfo

def get_pilotage_extraction_prompt(mail: MailObject) -> str:
    """
    Construit le prompt évaluant si un e-mail nécessite d'être mémorisé pour 
    le pilotage stratégique de l'établissement[cite: 18].
    
    Args:
        mail (MailObject): L'e-mail source à analyser.
        
    Returns:
        str: Le prompt visant à extraire l'information sous forme structurée.
    """
    pass

def get_pilotage_update_prompt(current_content: str, new_info: PilotageInfo) -> str:
    """
    Construit le prompt pour la mécanique de mise à jour ("Read-Rewrite-Replace")[cite: 29].
    Demande à l'agent de synthèse (Gemini Pro) [cite: 30] de réécrire et fusionner intelligemment la nouveauté 
    dans les rubriques concernées tout en conservant la structure globale intacte[cite: 31].
    
    Args:
        current_content (str): Le contenu Markdown brut du fichier central de pilotage.
        new_info (PilotageInfo): L'information synthétique à insérer.
        
    Returns:
        str: Le prompt contenant les instructions de fusion.
    """
    pass

def get_main_courante_update_prompt(mail: MailObject, existing_tags: List[str]) -> str:
    """
    Construit le prompt pour la mécanique de mise à jour ("Append" / Ajout continu).
    Demande de structurer chaque entrée avec un système de balises/tags précis[cite: 35].
    
    Args:
        mail (MailObject): L'e-mail source ayant déclenché l'événement.
        existing_tags (List[str]): Les tags extraits du fichier actuel, à réutiliser 
                                   prioritairement pour éviter les doublons[cite: 37].
        
    Returns:
        str: Le prompt générant le texte structuré de l'événement à ajouter.
    """
    pass
    
def get_agenda_extraction_prompt(mail: MailObject) -> str:
    """
    Construit le prompt pour l'extraction automatique de rendez-vous ou de tâches 
    afin de préparer les requêtes Google Tasks ou Calendar[cite: 23].
    
    Args:
        mail (MailObject): L'e-mail reçu et analysé.
        
    Returns:
        str: Le prompt ciblant la création d'un objet AgendaTaskRequest.
    """
    pass