from typing import Any
from src.core.models import MailObject, TriDecision

class TriageAgent:
    """
    Agent IA spécialisé dans le traitement rapide et le classement des e-mails entrants.
    Utilise de préférence un modèle très rapide (ex: Gemini Flash) pour ne pas 
    ralentir la boucle d'écoute IMAP.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        """
        Initialise le client de l'API Gemini pour le triage.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (str): Le nom du modèle à utiliser (Flash par défaut pour la vitesse).
        """
        pass

    def evaluate_email(self, mail: MailObject) -> TriDecision:
        """
        Analyse le contenu d'un e-mail et prend une décision de triage stricte.
        
        Le LLM est contraint par son System Prompt à retourner des données 
        structurées qui seront mappées directement dans l'objet Pydantic TriDecision.

        Args:
            mail (MailObject): L'objet représentant l'e-mail nettoyé.

        Returns:
            TriDecision: La décision de l'IA (dossier, priorité, justification).
        """
        pass