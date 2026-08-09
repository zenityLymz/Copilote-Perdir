from google.genai import types
from src.core.exceptions import AgentError
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service
from src.core.config import get_settings
from src.prompts.synth_prompts import get_hebdo_synthesis_system_prompt, build_hebdo_synthesis_prompt

logger = get_logger(__name__)

class SynthAgent:
    """Agent IA dédié à la génération du brouillon de synthèse hebdomadaire."""

    def __init__(self) -> None:
        try:
            self.router = get_gemini_router_service()
        except Exception as e:
            raise AgentError(f"Impossible d'initialiser l'Agent de Synthèse : {e}")

    async def generate_hebdo_brouillon(self, notes_text: str, memoire_structure: str) -> str:
        logger.info("Génération du brouillon de synthèse par le SynthAgent...")
        try:
            system_prompt = get_hebdo_synthesis_system_prompt()
            user_prompt = build_hebdo_synthesis_prompt(notes_text, memoire_structure)
            settings = get_settings()

            response = await self.router.generate_content(
                model_tier=settings.MODEL_SYNTHESIS_DOC,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2, 
                ),
                action_context="Brouillon_Synthese_Hebdo"
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini est vide.")

            # Nettoyage Markdown -> HTML pur
            html_content = response.text.strip()
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]

            return html_content.strip()

        except Exception as e:
            logger.error(f"Échec lors de la génération du brouillon : {e}", exc_info=True)
            raise AgentError(f"Erreur de l'agent de synthèse : {e}")