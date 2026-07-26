from src.core.models import MailObject

class TriagePromptManager:
    """
    Gestionnaire des prompts destinés à un agent spécialisé en tri rapide (Gemini Flash)[cite: 42].
    Définit les instructions pour évaluer l'urgence et classifier les e-mails.
    """

    @staticmethod
    def get_system_prompt() -> str:
        """
        Génère le prompt système global pour l'agent de triage.
        Contient les règles d'évaluation (niveaux de priorité, dossiers cibles).
        
        Returns:
            str: Le prompt système au format texte.
        """
        pass

    @staticmethod
    def build_mail_evaluation_prompt(mail: MailObject) -> str:
        """
        Construit le prompt utilisateur pour l'analyse d'un e-mail spécifique afin 
        de générer un objet TriDecision.
        
        Args:
            mail (MailObject): L'objet représentant l'e-mail entrant.
            
        Returns:
            str: Le prompt formaté contenant le corps et les métadonnées de l'e-mail.
        """
        pass