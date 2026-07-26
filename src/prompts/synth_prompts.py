from typing import List
from src.core.models import MailObject, PilotageInfo

class SynthPromptManager:
    """
    Gestionnaire des prompts destinés à un agent de synthèse (Gemini Pro)[cite: 42].
    Conçu pour les tâches d'analyse profonde nécessitant une manipulation 
    stratégique des données.
    """

    @staticmethod
    def get_pilotage_extraction_prompt(mail: MailObject) -> str:
        """
        Construit le prompt évaluant si un e-mail nécessite d'être mémorisé pour 
        le pilotage stratégique de l'établissement.
        
        Args:
            mail (MailObject): L'e-mail source à analyser.
            
        Returns:
            str: Le prompt visant à générer un objet PilotageInfo si pertinent.
        """
        pass

    @staticmethod
    def get_pilotage_update_prompt(current_content: str, new_info: PilotageInfo) -> str:
        """
        Construit le prompt pour la mécanique de mise à jour ("Read-Rewrite-Replace")[cite: 29].
        Demande au modèle de réécrire et fusionner intelligemment la nouveauté dans les rubriques concernées tout en conservant la structure globale strictement intacte[cite: 31].
        
        Args:
            current_content (str): Le contenu Markdown brut du fichier central de pilotage.
            new_info (PilotageInfo): L'information synthétique à insérer.
            
        Returns:
            str: Le prompt contenant les instructions de fusion.
        """
        pass

    @staticmethod
    def get_main_courante_update_prompt(mail: MailObject, existing_tags: List[str]) -> str:
        """
        Construit le prompt pour la mécanique de mise à jour ("Append" / Ajout continu)[cite: 34].
        Demande de structurer chaque entrée avec un système de balises/tags précis (ex: @Nom_Eleve, #Type_Incident)[cite: 35].
        
        Args:
            mail (MailObject): L'e-mail source ayant déclenché l'incident ou la remarque.
            existing_tags (List[str]): Les tags existants à réutiliser prioritairement.
            
        Returns:
            str: Le prompt générant le texte structuré de l'événement à ajouter à la fin du document.
        """
        pass
        
    @staticmethod
    def get_agenda_extraction_prompt(mail: MailObject) -> str:
        """
        Construit le prompt pour l'extraction automatique de rendez-vous ou de tâches 
        afin de préparer les requêtes Google Tasks ou Calendar.
        
        Args:
            mail (MailObject): L'e-mail reçu et analysé.
            
        Returns:
            str: Le prompt ciblant la création d'un objet AgendaTaskRequest.
        """
        pass