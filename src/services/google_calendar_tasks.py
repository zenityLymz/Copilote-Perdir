from typing import Any
from src.core.models import AgendaTaskRequest

class GoogleCalendarTasksService:
    """
    Gère les interactions avec Google Tasks et Google Calendar pour la création
    de rappels et d'événements extraits par l'IA.
    """

    def __init__(self, drive_service: Any) -> None:
        """
        Initialise le service en réutilisant l'authentification OAuth globale.

        Args:
            drive_service (Any): Instance authentifiée partageant les credentials.
        """
        pass

    def create_google_task(self, request: AgendaTaskRequest) -> str:
        """
        Crée une nouvelle tâche directement dans le Google Tasks de l'utilisateur.

        Args:
            request (AgendaTaskRequest): L'objet contenant le titre, la date limite et les notes.

        Returns:
            str: L'ID de la tâche créée.
        """
        pass

    def generate_calendar_link(self, request: AgendaTaskRequest) -> str:
        """
        Ne crée pas l'événement d'autorité, mais génère un lien URL d'insertion
        pré-rempli que le chef d'établissement pourra valider manuellement.

        Args:
            request (AgendaTaskRequest): Les paramètres de l'événement (Titre, date, description).

        Returns:
            str: Une URL cliquable formatée (ex: https://calendar.google.com/calendar/render?action=TEMPLATE...).
        """
        pass