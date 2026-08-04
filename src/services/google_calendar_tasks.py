import asyncio
from datetime import datetime, timedelta
import pytz
from typing import Any, List, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.core import AgendaTaskRequest, GoogleAPIError
from src.utils import get_logger

logger = get_logger(__name__)

class GoogleCalendarTasksService:
    """
    Gère les interactions avec Google Calendar (et Google Tasks) pour l'Agent IA.
    """

    def __init__(self, drive_service: Any) -> None:
        self.drive_service = drive_service
        self.token_path = getattr(drive_service, 'token_path', 'token.json')
        self.timezone = pytz.timezone("Europe/Paris")
        self._lock = asyncio.Lock()
        logger.debug("GoogleCalendarTasksService initialisé.")

    def _get_calendar_service(self):
        """Utilitaire pour instancier le client API Calendar."""
        try:
            creds = Credentials.from_authorized_user_file(self.token_path)
            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Impossible de construire le service Google Calendar : {e}")
            raise GoogleAPIError(f"Erreur d'authentification Agenda : {e}")

    # ==========================================
    # --- MÉTHODES GOOGLE CALENDAR (AGENDA) ---
    # ==========================================

    async def list_calendar_events(self, date_cible: datetime, date_fin: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Récupère les événements d'une journée ou d'une période spécifique."""
        async with self._lock:
            return await asyncio.to_thread(self._list_calendar_events_sync, date_cible, date_fin)

    def _list_calendar_events_sync(self, date_cible: datetime, date_fin: Optional[datetime]) -> List[Dict[str, Any]]:
        service = self._get_calendar_service()
        
        # Début de la période (00:00:00)
        start_of_day = date_cible.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Fin de la période (23:59:59 du jour cible ou du jour de fin)
        end_date = date_fin if date_fin else date_cible
        end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
        
        time_min = self.timezone.localize(start_of_day).isoformat()
        time_max = self.timezone.localize(end_of_day).isoformat()

        try:
            events_result = service.events().list(
                calendarId='primary', 
                timeMin=time_min,
                timeMax=time_max, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de l'agenda : {e}")
            raise GoogleAPIError(f"Lecture agenda échouée : {e}")

    async def create_calendar_event(self, request: AgendaTaskRequest, duree_minutes: int, lieu: Optional[str] = None) -> Dict[str, str]:
        """Crée un événement avec gestion du lieu."""
        async with self._lock:
            return await asyncio.to_thread(self._create_calendar_event_sync, request, duree_minutes, lieu)

    def _create_calendar_event_sync(self, request: AgendaTaskRequest, duree_minutes: int, lieu: Optional[str]) -> Dict[str, str]:
        service = self._get_calendar_service()
        
        start_dt = self.timezone.localize(request.date_cible)
        end_dt = start_dt + timedelta(minutes=duree_minutes)
        
        event_body = {
            'summary': request.titre,
            'description': request.description or "",
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Paris'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Paris'}
        }
        
        # Ajout du lieu s'il est spécifié (Google Calendar fera le lien Maps automatiquement)
        if lieu:
            event_body['location'] = lieu
            
        try:
            event = service.events().insert(calendarId='primary', body=event_body).execute()
            logger.info(f"Événement créé avec succès (ID: {event.get('id')}).")
            return {"id": event.get('id'), "link": event.get('htmlLink')}
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'événement : {e}")
            raise GoogleAPIError(f"Création événement échouée : {e}")

    async def delete_calendar_event(self, event_id: str) -> bool:
        """Supprime un événement via son ID."""
        async with self._lock:
            return await asyncio.to_thread(self._delete_calendar_event_sync, event_id)

    def _delete_calendar_event_sync(self, event_id: str) -> bool:
        service = self._get_calendar_service()
        try:
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            logger.info(f"Événement {event_id} supprimé avec succès.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'événement {event_id}: {e}")
            return False

    async def modify_calendar_event(self, event_id: str, new_date: Optional[datetime] = None, new_title: Optional[str] = None, duree_minutes: Optional[int] = None, lieu: Optional[str] = None, description: Optional[str] = None) -> str:
        """Met à jour partiellement (PATCH) un événement existant."""
        async with self._lock:
            return await asyncio.to_thread(self._modify_calendar_event_sync, event_id, new_date, new_title, duree_minutes, lieu, description)

    def _modify_calendar_event_sync(self, event_id: str, new_date: Optional[datetime], new_title: Optional[str], duree_minutes: Optional[int], lieu: Optional[str], description: Optional[str]) -> str:
        service = self._get_calendar_service()
        
        try:
            # On récupère l'événement existant
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Utilisation de "is not None" pour permettre d'effacer un champ en envoyant "" (chaîne vide)
            if new_title is not None:
                event['summary'] = new_title
            
            if lieu is not None:
                event['location'] = lieu
                
            if description is not None:
                event['description'] = description
                
            if new_date is not None:
                start_dt = self.timezone.localize(new_date)
                if not duree_minutes:
                    # On recalcule l'ancienne durée pour la conserver si non modifiée
                    old_start = datetime.fromisoformat(event['start'].get('dateTime'))
                    old_end = datetime.fromisoformat(event['end'].get('dateTime'))
                    duree_minutes = int((old_end - old_start).total_seconds() / 60)
                    
                end_dt = start_dt + timedelta(minutes=duree_minutes)
                
                event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Paris'}
                event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Paris'}
                
            updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
            logger.info(f"Événement {event_id} modifié avec succès.")
            return updated_event.get('htmlLink')
            
        except Exception as e:
            logger.error(f"Erreur lors de la modification de l'événement {event_id}: {e}")
            raise GoogleAPIError(f"Modification événement échouée : {e}")
        
    # ==========================================
    # --- MÉTHODES GOOGLE TASKS (TÂCHES) ---
    # ==========================================

    def _get_tasks_service(self):
        """Utilitaire pour instancier le client API Tasks."""
        try:
            creds = Credentials.from_authorized_user_file(self.token_path)
            return build('tasks', 'v1', credentials=creds)
        except Exception as e:
            logger.error(f"Impossible de construire le service Google Tasks : {e}")
            raise GoogleAPIError(f"Erreur d'authentification Tasks : {e}")

    async def list_google_tasks(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        """Récupère la liste des tâches (par défaut, uniquement celles non terminées)."""
        async with self._lock:
            return await asyncio.to_thread(self._list_google_tasks_sync, include_completed)

    def _list_google_tasks_sync(self, include_completed: bool) -> List[Dict[str, Any]]:
        service = self._get_tasks_service()
        try:
            # Récupère les tâches de la liste par défaut de l'utilisateur
            results = service.tasks().list(
                tasklist='@default', 
                showCompleted=include_completed,
                showHidden=False
            ).execute()
            return results.get('items', [])
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des tâches : {e}")
            raise GoogleAPIError(f"Lecture des tâches échouée : {e}")

    async def create_google_task(self, titre: str, date_cible: Optional[datetime] = None, description: Optional[str] = None) -> str:
        """Crée une nouvelle tâche et retourne son ID."""
        async with self._lock:
            return await asyncio.to_thread(self._create_google_task_sync, titre, date_cible, description)

    def _create_google_task_sync(self, titre: str, date_cible: Optional[datetime], description: Optional[str]) -> str:
        service = self._get_tasks_service()
        
        task_body = {'title': titre}
        if description:
            task_body['notes'] = description
        if date_cible:
            # Tasks API attend le format RFC3339
            task_body['due'] = date_cible.isoformat() + 'Z'
            
        try:
            result = service.tasks().insert(tasklist='@default', body=task_body).execute()
            logger.info(f"Tâche Google Tasks créée (ID: {result.get('id')}).")
            return result.get('id')
        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche Tasks : {e}")
            raise GoogleAPIError(f"Création de la tâche échouée : {e}")

    async def complete_google_task(self, task_id: str) -> bool:
        """Marque une tâche comme 'terminée' (cochée)."""
        async with self._lock:
            return await asyncio.to_thread(self._complete_google_task_sync, task_id)

    def _complete_google_task_sync(self, task_id: str) -> bool:
        service = self._get_tasks_service()
        try:
            # Utilisation de PATCH pour ne modifier que le statut sans écraser le reste
            service.tasks().patch(
                tasklist='@default', 
                task=task_id, 
                body={'status': 'completed'}
            ).execute()
            logger.info(f"Tâche {task_id} marquée comme terminée.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la validation de la tâche {task_id}: {e}")
            raise GoogleAPIError(f"Validation de la tâche échouée : {e}")

    async def delete_google_task(self, task_id: str) -> bool:
        """Supprime définitivement une tâche."""
        async with self._lock:
            return await asyncio.to_thread(self._delete_google_task_sync, task_id)

    def _delete_google_task_sync(self, task_id: str) -> bool:
        service = self._get_tasks_service()
        try:
            service.tasks().delete(tasklist='@default', task=task_id).execute()
            logger.info(f"Tâche {task_id} supprimée avec succès.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la tâche {task_id}: {e}")
            return False

    async def modify_google_task(self, task_id: str, new_title: Optional[str] = None, new_due: Optional[datetime] = None, new_notes: Optional[str] = None) -> str:
        """Met à jour une tâche existante (PATCH)."""
        async with self._lock:
            return await asyncio.to_thread(self._modify_google_task_sync, task_id, new_title, new_due, new_notes)

    def _modify_google_task_sync(self, task_id: str, new_title: Optional[str], new_due: Optional[datetime], new_notes: Optional[str]) -> str:
        service = self._get_tasks_service()
        try:
            # On récupère la tâche existante pour ne pas écraser les autres champs
            task = service.tasks().get(tasklist='@default', task=task_id).execute()
            
            # Utilisation de "is not None" pour permettre d'effacer les notes en envoyant ""
            if new_title is not None:
                task['title'] = new_title
                
            if new_notes is not None:
                task['notes'] = new_notes
                
            if new_due is not None:
                # L'API Google nécessite un format RFC 3339 mais ignorera l'heure
                task['due'] = new_due.isoformat() + 'Z'
                
            updated_task = service.tasks().update(tasklist='@default', task=task_id, body=task).execute()
            logger.info(f"Tâche {task_id} modifiée avec succès.")
            return updated_task.get('id')
        except Exception as e:
            logger.error(f"Erreur lors de la modification de la tâche {task_id}: {e}")
            raise GoogleAPIError(f"Modification de la tâche échouée : {e}")