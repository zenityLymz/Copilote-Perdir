from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from src.services.telegram_bot import TelegramBotService
from src.services.imap_service import IMAPService
from src.services.chroma_service import ChromaDBService
from src.services.google_drive_api import GoogleDriveService
from src.services.google_calendar_tasks import GoogleCalendarTasksService

from src.agents.router_agent import RouterAgent
from src.agents.rag_agent import RAGAgent
from src.agents.briefing_agent import BriefingAgent
from src.agents.main_courante_agent import MainCouranteAgent


class PipelineBTelegram:
    """
    Orchestrateur du Pipeline B (Actif) : Assistant Interactif Telegram.
    
    Ce workflow est déclenché par la réception d'un message (texte ou audio) 
    du chef d'établissement. Il délègue la compréhension de l'intention à 
    l'Agent Routeur, puis exécute l'une des 5 routes possibles :
    1. Agenda (Tâches/Calendrier)
    2. Recherche RAG (Interrogation de la mémoire vectorielle)
    3. Briefing (Synthèse des e-mails)
    4. Saisie Main Courante (Enregistrement d'un incident)
    5. Info Stratégique (Mise en mémoire tampon pour le traitement du soir)
    """

    def __init__(
        self,
        telegram_service: TelegramBotService,
        imap_service: IMAPService,
        chroma_service: ChromaDBService,
        drive_service: GoogleDriveService,
        calendar_service: GoogleCalendarTasksService,
        router_agent: RouterAgent,
        rag_agent: RAGAgent,
        briefing_agent: BriefingAgent,
        main_courante_agent: MainCouranteAgent
    ) -> None:
        """
        Initialise le Pipeline B avec tous les services et agents nécessaires 
        aux différentes routes conversationnelles.

        Args:
            telegram_service (TelegramBotService): Service pour répondre à l'utilisateur.
            imap_service (IMAPService): Pour la lecture des e-mails (Route Briefing).
            chroma_service (ChromaDBService): Base vectorielle (Route RAG).
            drive_service (GoogleDriveService): Accès au Drive (Main Courante & Tampon).
            calendar_service (GoogleCalendarTasksService): Gestion de l'agenda (Route Agenda).
            router_agent (RouterAgent): Agent standardiste (classification de l'intention).
            rag_agent (RAGAgent): Agent de synthèse documentaire.
            briefing_agent (BriefingAgent): Agent spécialisé dans le résumé d'inbox.
            main_courante_agent (MainCouranteAgent): Agent de formatage d'incidents.
        """
        pass

    async def process_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Point d'entrée principal appelé par le TelegramBotService lors de la 
        réception d'un message non-commande.
        
        Étapes :
        - Extraction du texte (ou transcription si c'est un message vocal).
        - Appel du RouterAgent pour déterminer la route métier à emprunter.
        - Aiguillage (switch/match) vers la méthode `_handle_*_route` correspondante.
        - Gestion globale des erreurs avec retour utilisateur bienveillant en cas d'échec.

        Args:
            update (Update): L'objet Update fourni par l'API Telegram.
            context (ContextTypes.DEFAULT_TYPE): Le contexte d'exécution Telegram.
        """
        pass

    async def _handle_agenda_route(self, user_text: str) -> None:
        """
        Gère la route "Agenda".
        Analyse la demande pour créer une tâche Google Tasks ou générer 
        un lien de création d'événement Google Calendar pré-rempli.
        Notifie l'utilisateur du succès sur Telegram.

        Args:
            user_text (str): La requête brute de l'utilisateur.
        """
        pass

    async def _handle_rag_search_route(self, user_text: str) -> None:
        """
        Gère la route "Recherche RAG".
        Vectorise la question, extrait les e-mails pertinents via ChromaDBService,
        soumet le contexte au RAGAgent pour formuler une réponse, et l'envoie sur Telegram.

        Args:
            user_text (str): La question posée par l'utilisateur.
        """
        pass

    async def _handle_briefing_route(self, user_text: str) -> None:
        """
        Gère la route "Briefing".
        Récupère les e-mails pertinents (urgents ou non lus) via IMAPService,
        fait appel au BriefingAgent pour générer un résumé structuré, et l'envoie sur Telegram.

        Args:
            user_text (str): La demande de l'utilisateur (peut inclure des précisions 
                             comme "donne-moi juste les urgences").
        """
        pass

    async def _handle_main_courante_route(self, user_text: str) -> None:
        """
        Gère la route "Saisie Main Courante" déclenchée manuellement via Telegram.
        Fait appel au MainCouranteAgent pour formater le texte brut en incident professionnel,
        puis l'ajoute au fichier Main_Courante.md via le GoogleDriveService.

        Args:
            user_text (str): La description factuelle de l'incident dictée par le Perdir.
        """
        pass

    async def _handle_strategic_buffer_route(self, user_text: str) -> None:
        """
        Gère la route "Info Stratégique (Tampon)".
        Enregistre une réflexion ou une information clé dans le fichier temporaire 
        'Tampon_Telegram.txt' sur Google Drive en attendant le traitement différé du Pipeline C.
        Confirme la bonne prise en compte à l'utilisateur.

        Args:
            user_text (str): L'information ou la réflexion stratégique à sauvegarder.
        """
        pass