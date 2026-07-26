from typing import List
from src.core.models import MailObject, TriDecision
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.telegram_bot import TelegramBotService
from src.agents.triage_agent import TriageAgent

class MailPipeline:
    """
    Workflow d'orchestration pour le traitement des e-mails.
    Gère la chaîne complète : Réception IMAP -> Décision IA (Triage) -> Action (Déplacement) 
    -> Mémorisation (ChromaDB) -> Alerte (Telegram).
    """

    def __init__(
        self,
        imap_service: IMAPService,
        triage_agent: TriageAgent,
        chroma_service: ChromaDBService,
        telegram_service: TelegramBotService
    ) -> None:
        """
        Initialise le pipeline avec toutes ses dépendances (injection de dépendances).
        Cela permet de découpler la logique métier de l'implémentation des services.

        Args:
            imap_service (IMAPService): Le service de connexion et manipulation IMAP.
            triage_agent (TriageAgent): L'agent IA (Gemini Flash) prenant les décisions de tri.
            chroma_service (ChromaDBService): La base vectorielle pour l'indexation sémantique.
            telegram_service (TelegramBotService): Le service pour l'envoi d'alertes au format asynchrone.
        """
        pass

    async def run_pipeline(self, folder: str = "INBOX", limit: int = 50) -> None:
        """
        Point d'entrée principal de la routine de traitement des e-mails.
        Doit être appelé régulièrement (ex: via une boucle de surveillance ou un cron interne).
        
        Étapes orchestrées :
        1. Fetch des e-mails non lus depuis le serveur IMAP.
        2. Boucle sur chaque e-mail pour le traiter individuellement.

        Args:
            folder (str): Le dossier IMAP à inspecter ("INBOX" par défaut).
            limit (int): Le nombre maximum d'e-mails à extraire par exécution pour éviter de saturer l'API.
        """
        pass

    async def _process_single_mail(self, mail: MailObject) -> None:
        """
        Sous-routine interne traitant un e-mail de bout en bout.
        Encapsule le traitement unitaire pour qu'une exception (ex: échec IA) sur un e-mail 
        ne fasse pas crasher l'ensemble du pipeline.

        Étapes orchestrées :
        1. Interrogation du TriageAgent pour obtenir une TriDecision.
        2. Indexation de l'e-mail dans le ChromaDBService.
        3. Déplacement de l'e-mail via l'IMAPService.
        4. Si decision.necessite_notification est Vrai, envoi d'une alerte via TelegramBotService.

        Args:
            mail (MailObject): L'objet e-mail modélisé à traiter.
        """
        pass