from typing import Optional, List, Callable
from google import genai
from google.genai import types

from src.core.models import ChatHistory
from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.utils.logger import get_logger

# Importation des constructeurs de prompts
from src.prompts.orchestrator_prompts import (
    get_orchestrator_system_prompt,
    build_orchestrator_prompt
)

# Importation de tous les outils (Function Calling) mis à disposition de l'IA
from src.tools import (
    creer_evenement_agenda, 
    creer_tache, 
    programmer_alerte, 
    ajouter_main_courante, 
    rechercher_document_drive, 
    rechercher_dans_les_emails, 
    enregistrer_brouillon_mail, 
    generer_briefing_emails
)

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class OrchestratorAgent:
    """
    Agent central et autonome du Pipeline B (Agentic Loop).
    Il gère la mémoire conversationnelle, raisonne sur l'intention de l'utilisateur, 
    et invoque dynamiquement des outils (Function Calling) si des actions sont nécessaires.
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour l'orchestrateur.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser.
        """
        try:
            settings = get_settings()
            # Initialisation du client SDK natif Google GenAI
            self.client = genai.Client(api_key=api_key)
            # Utilisation du modèle Flash par défaut, mais à voir plus tard selon les performances
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL
            
            logger.debug(f"OrchestratorAgent initialisé avec succès (Modèle: {self.model_name}).")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini (Orchestrateur) : {e}")
            raise AgentError(f"Impossible d'initialiser l'Orchestrateur : {e}")

    def _get_available_tools(self) -> List[Callable]:
        """
        Définit et retourne la liste des fonctions (outils) Python mises 
        à la disposition de l'agent.
        
        Returns:
            List[Callable]: Les références aux fonctions utilisables via le Function Calling.
        """
        return [
            creer_evenement_agenda,
            creer_tache,
            programmer_alerte,
            ajouter_main_courante,
            rechercher_document_drive,
            rechercher_dans_les_emails,
            enregistrer_brouillon_mail,
            generer_briefing_emails
        ]

    def _format_chat_history(self, chat_history: ChatHistory) -> List[types.Content]:
        """
        Convertit l'historique conversationnel local (Pydantic) au format 
        attendu par le SDK google-genai pour maintenir le contexte.

        Args:
            chat_history (ChatHistory): L'historique des échanges.

        Returns:
            List[types.Content]: La liste formatée pour l'API Gemini.
        """
        formatted_history = []
        for turn in chat_history.turns:
            # Le SDK exige que le rôle soit 'user' ou 'model'
            role = turn.role if turn.role in ["user", "model"] else "user"
            formatted_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn.message)]
                )
            )
        return formatted_history

    async def process_user_request(self, user_message: str, chat_history: ChatHistory) -> str:
        """
        Traite une nouvelle demande du chef d'établissement.
        L'agent analyse le contexte, vérifie s'il doit interroger l'utilisateur 
        pour des paramètres manquants, ou déclenche ses outils de façon autonome.

        Args:
            user_message (str): Le message texte (ou transcription audio) de l'utilisateur.
            chat_history (ChatHistory): L'historique des échanges pour le maintien du contexte.

        Returns:
            str: La réponse finale et naturelle formulée par l'IA.
        """
        logger.info("Début du cycle de raisonnement de l'Orchestrateur (Agentic Loop).")
        
        try:
            # 1. Préparation du contexte et des prompts
            system_prompt = get_orchestrator_system_prompt()
            # Injection dynamique de la date, heure, et alertes éventuelles
            enriched_user_prompt = build_orchestrator_prompt(user_message=user_message)
            formatted_history = self._format_chat_history(chat_history)

            # 2. Création de la session de chat asynchrone avec les outils injectés
            chat = self.client.aio.chats.create(
                model=self.model_name,
                history=formatted_history,
                config=types.ChatConfig(
                    system_instruction=system_prompt,
                    tools=self._get_available_tools(),
                    temperature=0.4, # Un peu de créativité pour le naturel, mais reste déterministe
                )
            )

            # 3. Envoi du message. 
            # Le SDK google-genai gère automatiquement l'exécution des fonctions Python (Function Calling)
            # si l'IA décide de les appeler, puis il renvoie la réponse finale synthétisée.
            response = await chat.send_message(enriched_user_prompt)

            if not response.text:
                raise AgentError("La réponse générée par l'Orchestrateur est vide.")

            logger.info("Cycle de l'Orchestrateur terminé avec succès.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec lors du traitement de la requête par l'Orchestrateur : {e}", exc_info=True)
            # Dégradation gracieuse : on ne fait pas crasher l'application, on remonte l'erreur
            return (
                "⚠️ Excusez-moi, j'ai rencontré une défaillance technique en essayant "
                "de traiter votre demande. Les services pourraient être temporairement indisponibles."
            )