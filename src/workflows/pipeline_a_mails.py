from typing import List, Optional

from src.core.models import MailObject, TriDecision
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.telegram_bot import TelegramBotService
from src.services.google_drive_api import GoogleDriveService
from src.agents.triage_agent import TriageAgent
from src.agents.main_courante_agent import MainCouranteAgent


class PipelineAMails:
    """
    Orchestrateur du Pipeline A (Passif) : Traitement Automatique des E-mails.
    
    Ce workflow écoute la boîte IMAP en tâche de fond, soumet les nouveaux e-mails 
    à l'Agent de Triage[cite: 19], et exécute automatiquement jusqu'à 4 actions :
    1. Alerte Telegram immédiate (si urgence)[cite: 20].
    2. Déplacement de l'e-mail dans le bon dossier IMAP[cite: 20].
    3. Indexation dans la base vectorielle ChromaDB (sauf poubelle)[cite: 21].
    4. Enregistrement d'un incident dans la Main Courante (si pertinent)[cite: 21].
    """

    def __init__(
        self,
        imap_service: IMAPService,
        triage_agent: TriageAgent,
        chroma_service: ChromaDBService,
        telegram_service: TelegramBotService,
        drive_service: GoogleDriveService,
        main_courante_agent: MainCouranteAgent
    ) -> None:
        """
        Initialise le Pipeline A avec l'ensemble des services et agents requis.
        L'injection de dépendances permet un découplage total de la logique métier.

        Args:
            imap_service (IMAPService): Connexion à la messagerie académique.
            triage_agent (TriageAgent): Agent IA (Flash) pour la prise de décision rapide.
            chroma_service (ChromaDBService): Base vectorielle pour la mémoire à long terme.
            telegram_service (TelegramBotService): Service d'envoi d'alertes push.
            drive_service (GoogleDriveService): Service Drive pour manipuler le fichier Markdown.
            main_courante_agent (MainCouranteAgent): Agent spécialisé pour le formatage des incidents.
        """
        pass

    async def run_pipeline(self, folder: str = "INBOX", limit: int = 50) -> None:
        """
        Point d'entrée principal de la boucle de traitement des e-mails.
        Destiné à être appelé à intervalles réguliers (polling non-bloquant).

        Étapes :
        - Récupération des e-mails non lus (UNSEEN) via IMAPService.
        - Itération asynchrone sur chaque e-mail pour déclencher `_process_single_mail`.

        Args:
            folder (str): Le dossier IMAP à écouter ("INBOX" par défaut).
            limit (int): Le nombre maximum d'e-mails à traiter par cycle pour limiter 
                         la charge système et les coûts API.
        """
        pass

    async def _process_single_mail(self, mail: MailObject) -> None:
        """
        Sous-routine traitant le cycle de vie complet d'un unique e-mail entrant.
        Gère les exceptions en isolation pour ne pas interrompre le pipeline global.

        Logique orchestrée (basée sur la TriDecision) :
        - Triage via TriageAgent.
        - Action 1 : Notification Telegram (si decision.necessite_notification)[cite: 20].
        - Action 2 : Déplacement IMAP vers decision.dossier_cible[cite: 20].
        - Action 3 : Indexation ChromaDB (ignorée si dossier_cible est "POUBELLE")[cite: 21].
        - Action 4 : Appel conditionnel à `_trigger_main_courante` si l'e-mail nécessite traçabilité[cite: 21].

        Args:
            mail (MailObject): L'objet e-mail pur à traiter.
        """
        pass

    async def _trigger_main_courante(self, mail: MailObject) -> bool:
        """
        Gère la mécanique "Read-Append-Replace" pour tracer un incident issu d'un e-mail[cite: 8].
        
        Étapes :
        - Téléchargement du fichier Main Courante actuel via GoogleDriveService.
        - Génération de la nouvelle entrée horodatée par le MainCouranteAgent.
        - Concaténation et écrasement du fichier sur le Drive.

        Args:
            mail (MailObject): L'e-mail source contenant les faits à consigner.

        Returns:
            bool: True si l'entrée a été générée et sauvegardée avec succès, False sinon.
        """
        pass