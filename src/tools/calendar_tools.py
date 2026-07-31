from typing import Optional
from datetime import datetime
from src.utils.logger import get_logger

# Initialisation du logger
logger = get_logger(__name__)

def creer_evenement_agenda(titre: str, date_heure_debut: str, duree_minutes: int, description: Optional[str] = None) -> bool:
    """
    Crée un nouvel événement (rendez-vous, réunion) directement dans le Google Calendar 
    du chef d'établissement.
    
    ATTENTION: Ne pas deviner la date et l'heure. Si l'utilisateur n'a pas précisé 
    le moment exact du rendez-vous, il faut l'interroger avant d'utiliser cet outil.

    Args:
        titre (str): Le nom de l'événement (ex: "Réunion Mairie", "Entretien Parent Dupont").
        date_heure_debut (str): La date et l'heure de début au format ISO 8601 (ex: "2026-07-31T14:00:00").
        duree_minutes (int): La durée estimée de l'événement en minutes (ex: 60, 90). Par défaut, estimer logiquement.
        description (Optional[str]): Informations complémentaires, ordre du jour ou lieu de la réunion.

    Returns:
        bool: True si l'événement a été ajouté à l'agenda avec succès, False sinon.
    """
    pass

def creer_tache(titre: str, echeance: Optional[str] = None, details: Optional[str] = None) -> bool:
    """
    Ajoute une nouvelle tâche (To-Do) à réaliser dans l'outil Google Tasks du chef d'établissement.
    
    Utiliser cet outil lorsque l'utilisateur exprime une action à faire à plus ou moins long terme, 
    sans lui assigner un créneau horaire bloqué dans l'agenda (ex: "Penser à valider les HSE des profs").

    Args:
        titre (str): L'intitulé court et direct de l'action à réaliser.
        echeance (Optional[str]): La date limite souhaitée au format ISO 8601 (ex: "2026-08-01"), si mentionnée.
        details (Optional[str]): Contexte supplémentaire ou notes d'exécution.

    Returns:
        bool: True si la tâche a été insérée avec succès, False sinon.
    """
    pass

def programmer_alerte(message_rappel: str, delai_minutes: int) -> bool:
    """
    Planifie l'envoi d'une notification Telegram (rappel) au chef d'établissement après 
    un temps donné.
    
    Utiliser cet outil lorsque l'utilisateur demande spécifiquement à être relancé ou 
    rappelé pour une action imminente (ex: "Rappelle-moi d'appeler l'infirmière dans 30 minutes").

    Args:
        message_rappel (str): Le texte exact du rappel à envoyer (ex: "Il est temps d'appeler l'infirmière").
        delai_minutes (int): Le nombre de minutes à attendre avant de déclencher l'alerte.

    Returns:
        bool: True si le minuteur a été activé avec succès, False sinon.
    """
    pass