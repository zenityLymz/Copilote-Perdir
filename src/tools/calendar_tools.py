import asyncio
from datetime import datetime
from typing import Optional

from src.utils import get_logger
from src.core import AgendaTaskRequest, get_drive_service, get_telegram_service
from src.services.google_calendar_tasks import GoogleCalendarTasksService

# Initialisation du logger
logger = get_logger(__name__)

async def gerer_agenda(action: str, date_cible: Optional[str] = None, date_fin: Optional[str] = None, titre: Optional[str] = None, duree_minutes: Optional[int] = 60, event_id: Optional[str] = None, description: Optional[str] = None, lieu: Optional[str] = None) -> str:
    """
    Outil universel (Couteau Suisse) pour lire, créer, modifier ou supprimer 
    des événements dans l'emploi du temps du chef d'établissement (Google Calendar).
    
    RÈGLES D'UTILISATION STRICTES :
    - Concernant l'action "creer" (ou l'action "modifier" si la modification porte sur la date de début et/ou la durée) : tu DOIS toujours au préalable utiliser l'action "lire" pour récupérer les événements de la journée et vérifier 
      les disponibilités à la date ciblée. Cela permet d'éviter les chevauchements (ou temps de trajet non pris en compte).
    - N'invente jamais ni de date ni d'heure : si l'utilisateur dit "Cale un rdv demain", demande-lui à quelle heure, s'il dit "Cale un rdv à 14h", demande-lui à quelle date.
    
    - Concernant l'action "modifier" : pour conserver la valeur existante d'un champ lors d'une modification, ne fournis pas le paramètre. Pour effacer intentionnellement la valeur d'un champ existant, fournis une chaîne vide "".
    - Cet outil ne gère QUE les rendez-vous, réunions et événements bloquant un créneau horaire. Il NE GÈRE PAS les tâches simples à cocher (utiliser l'outil des tâches pour cela).

    Args:
        action (str): L'action à effectuer. Doit être STRICTEMENT l'une de ces valeurs : "lire", "creer", "modifier", "supprimer".
        date_cible (Optional[str]): La date et l'heure ciblées au format ISO 8601 (ex: "2026-08-03T14:00:00"). Obligatoire pour "lire" et "creer".
        date_fin (Optional[str]): Utilisé uniquement pour l'action "lire" si on souhaite récupérer les événements sur plusieurs jours (ex: lire de lundi à mercredi).
        titre (Optional[str]): Le nom de l'événement. Requis pour "creer". Etre synthétique pour que cela reste lisible dans l'agenda (ex : "RDV Maire" et pas "Rendez-vous avec le maire pour discuter du projet de réhabilitation de la cour de récréation").
        duree_minutes (Optional[int]): La durée estimée en minutes. Par défaut 60.
        event_id (Optional[str]): L'identifiant technique de l'événement. OBLIGATOIRE pour "modifier" et "supprimer" (obtenu préalablement via l'action "lire").
        description (Optional[str]): Notes additionnelles ou ordre du jour.
        lieu (Optional[str]): L'adresse physique ou la salle (ex: "Rectorat de Besançon", "Salle des profs").

    Returns:
        str: Le résultat de l'opération, formaté pour que l'IA puisse le lire ou le transmettre.
    """
    logger.info(f"Outil 'gerer_agenda' appelé avec l'action : {action}")
    
    try:
        drive_service = get_drive_service()
        calendar_service = GoogleCalendarTasksService(drive_service)
        
        # 1. ACTION : LIRE (CONSULTER L'AGENDA)
        if action == "lire":
            if not date_cible:
                return "Erreur : le paramètre 'date_cible' est obligatoire pour lire l'agenda."
            
            dt_cible = datetime.fromisoformat(date_cible)
            dt_fin = datetime.fromisoformat(date_fin) if date_fin else None
            
            events = await calendar_service.list_calendar_events(dt_cible, dt_fin)
            
            période_texte = f"du {dt_cible.strftime('%d/%m/%Y')} au {dt_fin.strftime('%d/%m/%Y')}" if dt_fin else f"le {dt_cible.strftime('%d/%m/%Y')}"
            
            if not events:
                return f"L'agenda est totalement vide pour la période demandée ({période_texte})."
                
            result = f"Voici les événements prévus {période_texte} :\n\n"
            for ev in events:
                start = ev['start'].get('dateTime', ev['start'].get('date'))
                end = ev['end'].get('dateTime', ev['end'].get('date'))
                ev_id = ev['id']
                summary = ev.get('summary', 'Sans titre')
                location = ev.get('location', 'Aucun lieu précisé')
                
                # Formatage plus lisible pour les événements sur plusieurs jours ou journée entière
                is_all_day = 'T' not in start
                if is_all_day:
                    date_str = datetime.fromisoformat(start).strftime('%d/%m/%Y')
                    horaire = f"{date_str} (Journée entière)"
                else:
                    dt_start = datetime.fromisoformat(start)
                    dt_end = datetime.fromisoformat(end)
                    if dt_start.date() == dt_end.date():
                        horaire = f"{dt_start.strftime('%d/%m/%Y de %H:%M')} à {dt_end.strftime('%H:%M')}"
                    else:
                        horaire = f"Du {dt_start.strftime('%d/%m/%Y %H:%M')} au {dt_end.strftime('%d/%m/%Y %H:%M')}"
                
                result += f"- {horaire} : {summary} | Lieu : {location} | (ID technique: {ev_id})\n"
                
            return result
            
        # 2. ACTION : CRÉER UN ÉVÉNEMENT
        elif action == "creer":
            if not date_cible or not titre:
                return "Erreur : 'date_cible' et 'titre' sont obligatoires pour créer un événement."
                
            dt_cible = datetime.fromisoformat(date_cible)
            request = AgendaTaskRequest(
                type_action="événement_google_calendar",
                titre=titre,
                date_cible=dt_cible,
                description=description
            )
            
            result = await calendar_service.create_calendar_event(request, duree_minutes, lieu)
            return f"Succès. Événement créé. Lien d'accès : {result['link']}"
            
        # 3. ACTION : MODIFIER UN ÉVÉNEMENT
        elif action == "modifier":
            if not event_id:
                return "Erreur : 'event_id' est obligatoire pour modifier un événement. Utilise l'action 'lire' d'abord pour le trouver."
            
            dt_cible = datetime.fromisoformat(date_cible) if date_cible else None
            lien = await calendar_service.modify_calendar_event(event_id, dt_cible, titre, duree_minutes, lieu, description)
            return f"Succès. L'événement a été mis à jour. Lien d'accès : {lien}"

        # 4. ACTION : SUPPRIMER UN ÉVÉNEMENT
        elif action == "supprimer":
            if not event_id:
                return "Erreur : 'event_id' est obligatoire pour supprimer. Utilise l'action 'lire' d'abord pour le trouver."
                
            succes = await calendar_service.delete_calendar_event(event_id)
            if succes:
                return "L'événement a été définitivement supprimé de l'agenda."
            return "Échec de la suppression. L'ID fourni est peut-être invalide."
            
        else:
            return f"Erreur : L'action '{action}' n'est pas reconnue."

    except Exception as e:
        logger.error(f"Échec de l'outil gerer_agenda : {e}", exc_info=True)
        return "Erreur technique lors de l'interaction avec Google Calendar."

async def gerer_taches(action: str, titre: Optional[str] = None, echeance: Optional[str] = None, details: Optional[str] = None, task_id: Optional[str] = None) -> str:
    """
    Outil universel (Couteau Suisse) pour lire, créer, valider ou supprimer 
    les tâches à faire (To-Do List) du chef d'établissement dans Google Tasks.
    
    RÈGLES D'UTILISATION STRICTES :
    Cet outil NE GÈRE PAS les rendez-vous, réunions ou événements avec une heure de début et de fin (utiliser gerer_agenda pour cela). 
    Il gère les "choses à faire" (les tâches simples à cocher). Ces tâches n'ont pas d'heure de début, de fin ou de durée mais doivent être placée à une date donnée. Si la date n'est pas précisée, mettre la date du jour.
    - Action "lire" : liste les tâches en cours. À utiliser systématiquement avant "valider" ou "supprimer" pour obtenir les 'task_id'.
    - Action "modifier" : modifie le titre, la date ou les détails. Envoyer "" (chaîne vide) pour effacer les détails existants.
    - Action "valider" : permet de cocher une tâche comme étant "Fait / Terminée".
    - Action "supprimer" : supprime définitivement une tâche de la liste. À n'utiliser que sur demande de suppression explicite du perdir.

    Args:
        action (str): L'action à effectuer. Doit être STRICTEMENT l'une de ces valeurs : "lire", "creer", "modifier", "valider", "supprimer".
        titre (Optional[str]): L'intitulé court de l'action à réaliser. Requis pour "creer".
        echeance (Optional[str]): la date au format ISO 8601.
        details (Optional[str]): Contexte supplémentaire ou notes d'exécution.
        task_id (Optional[str]): L'identifiant technique de la tâche. OBLIGATOIRE pour "modifier", "valider" et "supprimer".

    Returns:
        str: Le résultat de l'opération ou la liste des tâches, formatée pour l'IA.
    """
    logger.info(f"Outil 'gerer_taches' appelé avec l'action : {action}")
    
    try:
        drive_service = get_drive_service()
        calendar_service = GoogleCalendarTasksService(drive_service)
        
        # 1. ACTION : LIRE (LISTER LES TÂCHES EN COURS)
        if action == "lire":
            tasks = await calendar_service.list_google_tasks(include_completed=False)
            
            if not tasks:
                return "Excellente nouvelle : il n'y a actuellement aucune tâche en attente dans la To-Do list !"
                
            result = "Voici la liste des tâches en attente :\n\n"
            for t in tasks:
                t_id = t['id']
                t_titre = t.get('title', 'Sans titre')
                t_notes = t.get('notes', '')
                t_due = t.get('due', '')
                
                # Formatage de l'échéance si présente
                echeance_str = " (Pas d'échéance)"
                if t_due:
                    # Google Tasks renvoie ex: '2026-08-01T00:00:00.000Z'
                    due_date = datetime.fromisoformat(t_due.replace('Z', '+00:00'))
                    echeance_str = f" [Échéance: {due_date.strftime('%d/%m/%Y')}]"
                
                notes_str = f" - Notes: {t_notes}" if t_notes else ""
                result += f"- {t_titre}{echeance_str}{notes_str} | (ID technique: {t_id})\n"
                
            return result
            
        # 2. ACTION : CRÉER UNE TÂCHE
        elif action == "creer":
            if not titre:
                return "Erreur : le 'titre' est obligatoire pour créer une tâche."
                
            dt_echeance = datetime.fromisoformat(echeance) if echeance else None
            await calendar_service.create_google_task(titre, dt_echeance, details)
            return f"La tâche '{titre}' a bien été ajoutée à Google Tasks."

        # 3. ACTION : MODIFIER UNE TÂCHE
        elif action == "modifier":
            if not task_id:
                return "Erreur : 'task_id' est obligatoire pour modifier. Utilise l'action 'lire' d'abord."
            dt_echeance = datetime.fromisoformat(echeance) if echeance else None
            await calendar_service.modify_google_task(task_id, titre, dt_echeance, details)
            return "La tâche a bien été mise à jour."
            
        # 4. ACTION : VALIDER (COCHER) UNE TÂCHE
        elif action == "valider":
            if not task_id:
                return "Erreur : 'task_id' est obligatoire pour valider une tâche. Utilise l'action 'lire' d'abord pour le trouver."
            
            await calendar_service.complete_google_task(task_id)
            return "Félicitations, la tâche a été cochée et marquée comme terminée avec succès."

        # 5. ACTION : SUPPRIMER UNE TÂCHE
        elif action == "supprimer":
            if not task_id:
                return "Erreur : 'task_id' est obligatoire pour supprimer. Utilise l'action 'lire' d'abord pour le trouver."
                
            succes = await calendar_service.delete_google_task(task_id)
            if succes:
                return "La tâche a été définitivement supprimée de la liste."
            return "Échec de la suppression. L'ID fourni est peut-être invalide."
            
        else:
            return f"Erreur : L'action '{action}' n'est pas reconnue."

    except Exception as e:
        logger.error(f"Échec de l'outil gerer_taches : {e}", exc_info=True)
        return "Erreur technique lors de l'interaction avec Google Tasks."



async def programmer_alerte(message_rappel: str, delai_minutes: int) -> str:
    """
    Planifie l'envoi d'une notification Telegram (rappel) au chef d'établissement après 
    un temps donné.
    
    Utiliser cet outil lorsque l'utilisateur demande spécifiquement à être relancé ou 
    rappelé pour une action imminente (ex: "Rappelle-moi d'appeler l'infirmière dans 30 minutes").

    Args:
        message_rappel (str): Le texte exact du rappel à envoyer (ex: "Il est temps d'appeler l'infirmière").
        delai_minutes (int): Le nombre de minutes à attendre avant de déclencher l'alerte.

    Returns:
        str: Message confirmant l'activation du minuteur pour l'IA.
    """
    logger.info(f"Outil 'programmer_alerte' appelé : '{message_rappel}' dans {delai_minutes} minutes.")
    
    try:
        delai_secondes = delai_minutes * 60
        
        # 1. On définit la fonction qui tournera en tâche de fond
        async def alerte_en_arriere_plan():
            await asyncio.sleep(delai_secondes)
            logger.info(f"⏰ DRING ! Fin du minuteur. Envoi du message : {message_rappel}")
            
            telegram_service = get_telegram_service()
            await telegram_service.send_notification(f"⏰ <b>RAPPEL MINUTEUR</b>\n\n{message_rappel}")
            
        # 2. On lance la tâche en arrière-plan (cela ne bloque pas le script principal)
        asyncio.create_task(alerte_en_arriere_plan())
        
        return f"Succès. Le minuteur est lancé. L'utilisateur sera rappelé de '{message_rappel}' dans {delai_minutes} minutes."
        
    except Exception as e:
        logger.error(f"Échec de l'outil programmer_alerte : {e}", exc_info=True)
        return "Erreur technique lors de la programmation du rappel."