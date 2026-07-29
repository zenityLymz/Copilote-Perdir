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
        self.message = message
        super().__init__(self.message)


class WorkflowError(AssistantPerdirError):
    """
    Exception levée par les orchestrateurs (Pipelines A, B, C) lorsqu'une 
    logique métier globale échoue (ex: échec d'agrégation de données, route introuvable).
    """
    def __init__(self, message: str = "Erreur lors de l'exécution d'un workflow métier.") -> None:
        super().__init__(message)


class IMAPError(AssistantPerdirError):
    """
    Exception levée lors d'un problème d'interaction avec le serveur de messagerie académique.
    (Exemples : échec d'authentification, perte de connexion, dossier introuvable).
    """
    def __init__(self, message: str = "Erreur de communication avec le serveur IMAP.") -> None:
        """
        Initialise l'exception IMAP.
        
        Args:
            message (str): Message d'erreur personnalisé.
        """
        super().__init__(message)


class AgentError(AssistantPerdirError):
    """
    Exception levée lorsqu'un modèle d'IA (Gemini Flash ou Pro) rencontre une défaillance.
    (Exemples : timeout de l'API Google, format de réponse inattendu, erreur de parsing JSON).
    """
    def __init__(self, message: str = "Défaillance lors de l'interaction avec l'agent IA (Gemini).") -> None:
        """
        Initialise l'exception de l'Agent IA.
        
        Args:
            message (str): Message d'erreur personnalisé.
        """
        super().__init__(message)


class GoogleAPIError(AssistantPerdirError):
    """
    Exception levée lors d'un échec d'interaction avec l'écosystème Google Workspace via OAuth 2.0.
    (Exemples : token expiré ou invalide, fichier Markdown introuvable sur le Drive, quota dépassé).
    """
    def __init__(self, message: str = "Erreur lors de l'interaction avec l'API Google Workspace.") -> None:
        """
        Initialise l'exception Google API.
        
        Args:
            message (str): Message d'erreur personnalisé.
        """
        super().__init__(message)


class ChromaDBError(AssistantPerdirError):
    """
    Exception levée en cas de dysfonctionnement de la base de données vectorielle locale.
    (Exemples : corruption du dossier persistant, échec de génération des embeddings, erreur de recherche).
    """
    def __init__(self, message: str = "Erreur liée à la base de données vectorielle ChromaDB.") -> None:
        """
        Initialise l'exception ChromaDB.
        
        Args:
            message (str): Message d'erreur personnalisé.
        """
        super().__init__(message)


class TelegramBotError(AssistantPerdirError):
    """
    Exception levée lors d'un problème de communication avec l'API Telegram.
    (Exemples : jeton invalide, message tronqué ou trop long, erreur réseau en mode Long Polling).
    """
    def __init__(self, message: str = "Erreur de communication avec le bot Telegram.") -> None:
        """
        Initialise l'exception du Bot Telegram.
        
        Args:
            message (str): Message d'erreur personnalisé.
        """
        super().__init__(message)