from google.genai import types
from src.core.exceptions import AgentError
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service
from src.prompts.draft_prompts import get_draft_system_prompt, build_draft_user_prompt

logger = get_logger(__name__)

class DraftAgent:
    """
    Agent IA dédié à la rédaction de brouillons d'e-mails.
    Il utilise une approche "Few-Shot" basée sur un guide de style statique
    pour imiter parfaitement la voix du chef d'établissement.
    """

    def __init__(self) -> None:
        try:
            self.router = get_gemini_router_service()
            logger.debug("DraftAgent initialisé avec succès via GeminiRouterService.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du DraftAgent : {e}")
            raise AgentError(f"Impossible d'initialiser le DraftAgent : {e}")

    async def generate_draft(self, destinataire: str, sujet: str, contexte_original: str, directives_de_redaction: str) -> str:
        """
        Génère le texte final du brouillon d'e-mail.
        """
        logger.info(f"DraftAgent: Génération d'un brouillon pour {destinataire}.")
        
        try:
            system_prompt = get_draft_system_prompt()
            user_prompt = build_draft_user_prompt(destinataire, sujet, contexte_original, directives_de_redaction)

            # On force le modèle "flash" (idéal pour le respect de style via Few-Shot)
            response = await self.router.generate_content(
                model_tier="flash", 
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Température basse (0.2) pour éviter que l'IA ne dérive du style imposé
                    temperature=0.2, 
                ),
                action_context="Redaction_Brouillon_Email",
                force_paid=True
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini (DraftAgent) est vide.")

            logger.info("DraftAgent: Brouillon stylisé généré avec succès.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec de la génération du brouillon stylisé : {e}", exc_info=True)
            raise AgentError(f"Erreur du DraftAgent : {e}")