from typing import Optional
from src.core.models import MailObject
from src.services.google_drive_api import GoogleDriveService
from src.services.telegram_bot import TelegramBotService
from src.agents.synth_agent import SynthAgent

class StrategicMemoryWorkflow:
    """
    Workflow d'orchestration pour la gestion de la mémoire à long terme de l'IA.
    Gère la mise à jour du Fichier de Pilotage Stratégique et du Dossier de Main Courante
    (qui sont tous les deux des fichiers Markdown centralisés sur Google Drive).
    """

    def __init__(
        self,
        drive_service: GoogleDriveService,
        synth_agent: SynthAgent,
        telegram_service: TelegramBotService,
        pilotage_file_id: str,
        main_courante_file_id: str
    ) -> None:
        """
        Initialise le workflow avec les services nécessaires et les identifiants des fichiers.

        Args:
            drive_service (GoogleDriveService): Service pour manipuler les fichiers bruts (.md) sur le Drive.
            synth_agent (SynthAgent): Agent IA (Gemini Pro) pour l'analyse et la réécriture du Markdown.
            telegram_service (TelegramBotService): Service pour informer l'utilisateur des mises à jour.
            pilotage_file_id (str): L'ID Google Drive du fichier Markdown de Pilotage Stratégique.
            main_courante_file_id (str): L'ID Google Drive du fichier Markdown de Main Courante.
        """
        pass

    async def update_pilotage_memory(self, new_info: str) -> bool:
        """
        Orchestre la mécanique 'Read-Rewrite-Replace' pour le Fichier de Pilotage.
        
        Étapes orchestrées :
        1. Read : Téléchargement du contenu actuel du fichier Markdown via GoogleDriveService.
        2. Rewrite : Demande au SynthAgent de fusionner la nouvelle information dans le bon chapitre.
        3. Replace : Écrasement du fichier sur le Drive avec le nouveau contenu généré.
        4. Notification : Envoi d'un message Telegram pour confirmer la prise en compte.

        Args:
            new_info (str): La nouvelle information stratégique brute à intégrer.

        Returns:
            bool: True si le cycle complet de mise à jour a réussi, False sinon.
        """
        pass

    async def append_main_courante_event(self, raw_event: str) -> bool:
        """
        Orchestre la mécanique 'Read-Append-Replace' pour le journal de Main Courante.
        
        Étapes orchestrées :
        1. Read : Téléchargement du contenu actuel du fichier Markdown pour analyser l'historique des tags.
        2. Append : Demande au SynthAgent de formater la nouvelle entrée horodatée avec les bons tags.
        3. Replace : Ajout (concaténation) du texte généré au document et écrasement sur le Drive.
        4. Notification : Envoi d'une confirmation de traçabilité via Telegram.

        Args:
            raw_event (str): La description brute de l'événement sensible à tracer.

        Returns:
            bool: True si l'événement a bien été consigné, False sinon.
        """
        pass

    async def process_autonomous_extraction(self, mail: MailObject) -> None:
        """
        Fonction d'analyse autonome déclenchée lors de la réception d'un e-mail.
        Évalue si l'e-mail contient des informations justifiant une mise à jour 
        stratégique ou un signalement dans la main courante, sans intervention humaine.

        Si l'agent détecte une information pertinente, cette méthode appelle 
        automatiquement `update_pilotage_memory` ou `append_main_courante_event`.

        Args:
            mail (MailObject): L'objet e-mail à analyser pour extraction potentielle.
        """
        pass