import asyncio
from datetime import timedelta
from urllib.parse import urlencode
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.core.models import AgendaTaskRequest
from src.utils.logger import get_logger
from src.core.exceptions import GoogleAPIError

# Initialisation du logger pour ce module
logger = get_logger(__name__)

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
        self.drive_service = drive_service
        # On extrait le chemin vers token.json porté par le service Drive, 
        # sinon on prend la valeur par défaut
        self.token_path = getattr(drive_service, 'token_path', 'token.json')
        
        
        logger.debug("GoogleCalendarTasksService initialisé.")

    async def create_google_task(self, request: AgendaTaskRequest) -> str:
        """
        Crée une nouvelle tâche directement dans le Google Tasks de l'utilisateur.
        Exécuté de manière asynchrone pour ne pas bloquer le bot.

        Args:
            request (AgendaTaskRequest): L'objet contenant le titre, la date limite et les notes.

        Returns:
            str: L'ID de la tâche créée.
        """
        return await asyncio.to_thread(self._create_google_task_sync, request)

    def _create_google_task_sync(self, request: AgendaTaskRequest) -> str:
        """
        Logique synchrone de création de tâche, exécutée dans un thread séparé.
        """
        try:
            logger.debug(f"Tentative de création d'une tâche Tasks : {request.titre}")
            
            # Récupération des accès via le fichier généré par le service Drive
            creds = Credentials.from_authorized_user_file(self.token_path)
            
            # Instanciation du client Tasks API
            service = build('tasks', 'v1', credentials=creds)
            
            # Préparation du payload
            task_body = {
                'title': request.titre,
            }
            
            if request.description:
                task_body['notes'] = request.description
                
            if request.date_cible:
                # L'API Google Tasks exige le format RFC 3339 pour la date d'échéance
                task_body['due'] = request.date_cible.isoformat() + 'Z'
                
            # Appel à l'API Google dans la liste de tâches par défaut
            result = service.tasks().insert(tasklist='@default', body=task_body).execute()
            
            task_id = result.get('id')
            logger.info(f"Tâche Google Tasks créée avec succès (ID: {task_id}).")
            return task_id
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche Google Tasks : {e}")
            raise GoogleAPIError(f"Création de la tâche échouée : {e}")

    def generate_calendar_link(self, request: AgendaTaskRequest) -> str:
        """
        Ne crée pas l'événement d'autorité, mais génère un lien URL d'insertion
        pré-rempli que le chef d'établissement pourra valider manuellement.

        Args:
            request (AgendaTaskRequest): Les paramètres de l'événement (Titre, date, description).

        Returns:
            str: Une URL cliquable formatée (ex: https://calendar.google.com/calendar/render?action=TEMPLATE...).
        """
        base_url = "https://calendar.google.com/calendar/render"
        
        params = {
            'action': 'TEMPLATE',
            'text': request.titre,
        }
        
        if request.description:
            params['details'] = request.description
            
        if request.date_cible:
            # On génère un créneau d'1 heure par défaut à partir de la date ciblée
            start_dt = request.date_cible
            end_dt = start_dt + timedelta(hours=1)
            
            # Format attendu par Google Calendar : YYYYMMDDTHHMMSS 
            # (Sans le 'Z' à la fin, l'événement utilisera automatiquement le fuseau horaire de l'utilisateur)
            start_str = start_dt.strftime("%Y%m%dT%H%M%S")
            end_str = end_dt.strftime("%Y%m%dT%H%M%S")
            params['dates'] = f"{start_str}/{end_str}"
            
        # Encodage sécurisé de l'URL
        query_string = urlencode(params)
        link = f"{base_url}?{query_string}"
        
        logger.info(f"Lien Google Calendar généré avec succès pour : '{request.titre}'.")
        return link