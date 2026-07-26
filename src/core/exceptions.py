"""
Module des exceptions personnalisées (exceptions)

Ce module définit toutes les erreurs spécifiques à l'application "Assistant IA Intégral".
Centraliser ces exceptions permet de faciliter le débogage, d'améliorer la lisibilité 
des logs et de garantir une gestion d'erreurs (try/except) granulaire.
"""

class AssistantPerdirError(Exception):
    """
    Classe de base pour toutes les exceptions personnalisées du projet.
    Permet de capturer globalement n'importe quelle erreur métier si nécessaire.
    """
    def __init__(self, message: str) -> None:
        """
        Initialise l'exception avec un message d'erreur explicite.

        Args:
            message (str): La description détaillée de l'erreur rencontrée.
        """
        pass


class IMAPError(AssistantPerdirError):
    """
    Exception levée lors d'un problème d'interaction avec le serveur de messagerie académique.
    (Exemples : échec d'authentification, perte de connexion, dossier introuvable).
    """
    pass


class AgentError(AssistantPerdirError):
    """
    Exception levée lorsqu'un modèle d'IA (Gemini Flash ou Pro) rencontre une défaillance.
    (Exemples : timeout de l'API Google, format de réponse inattendu, erreur de parsing JSON).
    """
    pass


class GoogleAPIError(AssistantPerdirError):
    """
    Exception levée lors d'un échec d'interaction avec l'écosystème Google Workspace via OAuth 2.0.
    (Exemples : token expiré ou invalide, fichier Markdown introuvable sur le Drive, quota dépassé).
    """
    pass


class ChromaDBError(AssistantPerdirError):
    """
    Exception levée en cas de dysfonctionnement de la base de données vectorielle locale.
    (Exemples : corruption du dossier persistant, échec de génération des embeddings, erreur de recherche).
    """
    pass


class TelegramBotError(AssistantPerdirError):
    """
    Exception levée lors d'un problème de communication avec l'API Telegram.
    (Exemples : jeton invalide, message tronqué ou trop long, erreur réseau en mode Long Polling).
    """
    pass