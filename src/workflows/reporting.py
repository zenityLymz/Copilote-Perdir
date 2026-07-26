from typing import List, Optional
from src.services.imap_service import IMAPService
from src.services.telegram_bot import TelegramBotService
from src.agents.synth_agent import SynthAgent
from src.core.models import MailObject

class ReportingWorkflow:
    """
    Workflow d'orchestration pour la génération de rapports et de synthèses.
    Gère principalement la création de briefings à la demande pour donner 
    au chef d'établissement une vision claire des urgences et tâches en attente.
    """

    def __init__(
        self,
        imap_service: IMAPService,
        synth_agent: SynthAgent,
        telegram_service: TelegramBotService
    ) -> None:
        """
        Initialise le workflow de reporting avec ses dépendances.

        Args:
            imap_service (IMAPService): Service pour récupérer les e-mails en attente.
            synth_agent (SynthAgent): Agent IA (Gemini Pro) capable de résumer et synthétiser de multiples e-mails.
            telegram_service (TelegramBotService): Service pour envoyer le rapport final au format asynchrone.
        """
        pass

    async def generate_inbox_briefing(self, folder: str = "INBOX", limit: int = 20) -> bool:
        """
        Routine générant un briefing synthétique des messages en attente.
        
        Étapes orchestrées :
        1. Récupération des e-mails non lus via l'IMAPService.
        2. Si la boîte est vide, envoi d'un message rassurant via Telegram.
        3. Sinon, soumission de la liste des e-mails au SynthAgent pour générer un résumé structuré.
        4. Envoi du briefing formaté au chef d'établissement via TelegramBotService.

        Args:
            folder (str): Le dossier à analyser (généralement la boîte de réception principale).
            limit (int): Le nombre maximum d'e-mails à inclure dans le briefing pour éviter la surcharge.

        Returns:
            bool: True si le briefing a été généré et envoyé avec succès, False sinon.
        """
        pass

    async def _format_and_send_alert(self, summary_text: str) -> None:
        """
        Sous-routine utilitaire pour formater (Markdown/HTML) et tronquer si besoin
        le texte du briefing avant son envoi sur Telegram, afin de respecter 
        les limites de caractères de l'API Telegram.

        Args:
            summary_text (str): Le texte brut du briefing généré par l'IA.
        """
        pass