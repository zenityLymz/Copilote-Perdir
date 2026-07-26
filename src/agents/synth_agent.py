from typing import List, Optional
from src.core.models import MailObject, AgendaTaskRequest

class SynthAgent:
    """
    Agent IA spécialisé dans l'analyse stratégique complexe et la structuration de textes.
    Utilise un modèle avancé (ex: Gemini Pro) pour analyser l'impact d'une information 
    et formater rigoureusement des fichiers Markdown (Pilotage et Main Courante).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro") -> None:
        """
        Initialise le client de l'API Gemini pour les tâches de synthèse complexes.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (str): Le nom du modèle à utiliser (Pro recommandé pour le raisonnement).
        """
        pass

    def rewrite_pilotage_content(self, current_markdown: str, new_info: str) -> str:
        """
        Applique la mécanique "Read-Rewrite-Replace" pour le Fichier Pilotage.
        Évalue l'impact de la nouvelle information, fusionne intelligemment les 
        données dans les rubriques concernées du Markdown sans altérer sa structure.

        Args:
            current_markdown (str): Le contenu intégral actuel du fichier de pilotage.
            new_info (str): La nouvelle information stratégique brute à intégrer.

        Returns:
            str: Le nouveau contenu Markdown complet, prêt à écraser l'ancien fichier.
        """
        pass

    def format_main_courante_entry(self, current_markdown: str, raw_event: str) -> str:
        """
        Prépare une nouvelle entrée pour le dossier Main Courante (Append).
        Analyse le fichier existant pour réutiliser les tags pertinents (@Nom, #Incident) 
        et génère le texte de la nouvelle entrée horodatée avec le bon balisage.

        Args:
            current_markdown (str): Le contenu intégral actuel (pour lire l'historique des tags).
            raw_event (str): La description brute de l'événement à consigner.

        Returns:
            str: La nouvelle entrée formatée en Markdown, prête à être concaténée au fichier.
        """
        pass

    def extract_agenda_tasks(self, mail: MailObject) -> List[AgendaTaskRequest]:
        """
        Analyse un e-mail profond pour en extraire des actions ou des événements d'agenda.
        Cette méthode est utilisée si l'e-mail requiert une action planifiée.

        Args:
            mail (MailObject): L'e-mail source à analyser.

        Returns:
            List[AgendaTaskRequest]: Une liste d'objets modélisant les tâches ou RDVs à créer.
        """
        pass