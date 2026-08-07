from typing import Optional, List, Callable
from google import genai
from google.genai import types

from src.core.models import ChatHistory
from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.core.dependencies import get_drive_service
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service

# Importation des constructeurs de prompts
from src.prompts.orchestrator_prompts import (
    get_orchestrator_system_prompt,
    build_orchestrator_prompt
)

# Importation de tous les outils (Function Calling) mis à disposition de l'IA
from src.tools import (
    gerer_agenda, 
    gerer_taches,
    programmer_alerte, 
    preparer_brouillon_main_courante,
    sauvegarder_main_courante_validee,
    rechercher_info_drive,
    lire_memoire_etablissement,
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

    def __init__(self) -> None:
        """
        Initialise le client de l'API Gemini pour l'orchestrateur.

        """
        try:
            self.router = get_gemini_router_service()
            
            logger.debug(f"OrchestratorAgent initialisé avec succès via GeminiRouterService.")
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
            gerer_agenda,
            gerer_taches,
            programmer_alerte,
            preparer_brouillon_main_courante,
            sauvegarder_main_courante_validee,
            rechercher_info_drive,
            lire_memoire_etablissement,
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

    # Téléchargement asynchrone de la mémoire de l'établissement depuis le Drive pour enrichir le prompt
    async def _fetch_memoire_etablissement(self) -> Optional[str]:
        """
        Récupère le contenu du document Mémoire de l'Établissement depuis le Drive.
        Gère les erreurs silencieusement pour ne pas bloquer l'Orchestrateur.
        """
        try:
            settings = get_settings()
            drive_service = get_drive_service()
            file_id = settings.MEMOIRE_FILE_ID
            
            logger.debug("Téléchargement de la mémoire de l'établissement depuis Google Drive...")
            # On utilise l'exportation en TEXTE BRUT pour diviser le poids du prompt par 10 !
            content = await drive_service.get_file_text_content(
                file_id=file_id, 
                mime_type='application/vnd.google-apps.document'
            )
            return content
        except Exception as e:
            # Dégradation gracieuse : On loggue l'erreur mais on ne crashe pas
            logger.warning(f"Impossible de récupérer la mémoire de l'établissement (Drive injoignable ?) : {e}")
            return None

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
            
            enriched_user_prompt = build_orchestrator_prompt(
                user_message=user_message
            )
            formatted_history = self._format_chat_history(chat_history)

            settings = get_settings()
            
            # 3. Création de la session de chat asynchrone avec les outils injectés
            response = await self.router.send_chat_message(
                model_tier=settings.MODEL_ORCHESTRATOR,
                history=formatted_history,
                user_message=enriched_user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=self._get_available_tools(),
                    temperature=0.4,
                ),
                action_context="Orchestrateur_Agentic_Loop"
            )

            if not response.text:
                raise AgentError("La réponse générée par l'Orchestrateur est vide.")

            # --- Filet de sécurité (car normalement géré par le prompt) : Nettoyage et conversion forcée du Markdown en HTML
            import re
            final_text = response.text.strip()
            
            # 1. Convertir le gras Markdown (**texte**) en HTML (<b>texte</b>)
            final_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', final_text)
            
            # 2. Convertir les gros titres Markdown (### Titre) en HTML (<b>Titre</b>)
            final_text = re.sub(r'^#+\s+(.+)$', r'<b>\1</b>', final_text, flags=re.MULTILINE)
            # --------------------------------------------------------------------

            logger.info("Cycle de l'Orchestrateur terminé avec succès.")
            return final_text

        except Exception as e:
            logger.error(f"Échec lors du traitement de la requête par l'Orchestrateur : {e}", exc_info=True)
            # Dégradation gracieuse : on ne fait pas crasher l'application, on remonte l'erreur
            return (
                "⚠️ Excusez-moi, j'ai rencontré une défaillance technique en essayant "
                "de traiter votre demande. Les services pourraient être temporairement indisponibles."
            )