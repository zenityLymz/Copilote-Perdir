from google import genai
from google.genai import types
from pydantic import ValidationError

from src.core.models import MailObject, IA_TriResponse, TriDecision
from src.core.exceptions import AgentError
from src.prompts.triage_prompts import get_triage_system_prompt, build_mail_evaluation_prompt
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class TriageAgent:
    """
    Agent IA spécialisé dans le traitement rapide et le classement des e-mails entrants.
    Utilise de préférence un modèle très rapide (ex: Gemini Flash) pour ne pas 
    ralentir la boucle d'écoute IMAP.
    """

    def __init__(self) -> None:
        """
        Initialise le client de l'API Gemini pour le triage.

        """
        try:
            self.router = get_gemini_router_service()
            logger.debug("TriageAgent initialisé avec succès via GeminiRouterService.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de l'agent de triage : {e}")
            raise AgentError(f"Impossible d'initialiser l'agent de triage : {e}")

    async def evaluate_email(self, mail: MailObject) -> TriDecision:
        """
        Analyse le contenu d'un e-mail de manière asynchrone et prend une décision de triage stricte.
        
        Le LLM est contraint par son System Prompt à retourner des données 
        structurées qui seront mappées directement dans l'objet Pydantic TriDecision.

        Args:
            mail (MailObject): L'objet représentant l'e-mail nettoyé.

        Returns:
            TriDecision: La décision de l'IA (dossier, priorité, justification).
        """
        try:
            logger.debug(f"Demande de triage asynchrone pour l'e-mail ID: {mail.id_mail} ('{mail.sujet}')")
            
            # 1. Récupération des prompts
            system_prompt = get_triage_system_prompt()
            user_prompt = build_mail_evaluation_prompt(mail)

            # 2. Appel à l'API Gemini via notre routeur central (Gestion 429 et Tracker)
            response = await self.router.generate_content(
                model_tier="flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=IA_TriResponse,
                    temperature=0.1 
                ),
                action_context=f"Triage_Mail_{mail.id_mail}"
            )

            # 3. Nettoyage de sécurité du JSON brut (Suppression des balises Markdown parasites)
            raw_json = response.text.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            elif raw_json.startswith("```"):
                raw_json = raw_json[3:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
                
            raw_json = raw_json.strip()

            # 4. Parsing de la réponse de l'IA nettoyée
            ia_response = IA_TriResponse.model_validate_json(raw_json)
            
            # 5. Assemblage sécurisé de l'objet métier final par le code Python
            decision = TriDecision(
                id_mail=mail.id_mail,
                **ia_response.model_dump() # On déverse les champs générés par l'IA
            )
            
            logger.info(
                f"Décision de tri prise [E-mail {decision.id_mail}] -> "
                f"Dossier: '{decision.dossier_cible.value}', "
                f"Alerte: {decision.necessite_notification}"
            )
            
            return decision

        except ValidationError as e:
            logger.error(f"Erreur de validation Pydantic de la réponse IA pour l'e-mail {mail.id_mail} : {e}")
            raise AgentError(f"Le format renvoyé par l'IA ne correspond pas à TriDecision : {e}")
            
        except Exception as e:
            logger.error(f"Échec de l'évaluation asynchrone de l'e-mail {mail.id_mail} par l'IA : {e}")
            raise AgentError(f"Erreur lors de l'appel à l'API Gemini via Routeur : {e}")