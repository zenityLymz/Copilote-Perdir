from google import genai
from google.genai import types
from pydantic import ValidationError

from src.core.models import MailObject, IA_TriResponse, TriDecision
from src.core.exceptions import AgentError
from src.prompts.triage_prompts import get_triage_system_prompt, build_mail_evaluation_prompt
from src.utils.logger import get_logger
from src.core.config import get_settings

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class TriageAgent:
    """
    Agent IA spécialisé dans le traitement rapide et le classement des e-mails entrants.
    Utilise de préférence un modèle très rapide (ex: Gemini Flash) pour ne pas 
    ralentir la boucle d'écoute IMAP.
    """

    def __init__(self, api_key: str, model_name: str = None) -> None:
        """
        Initialise le client de l'API Gemini pour le triage.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (str): Le nom du modèle à utiliser (Flash par défaut pour la vitesse).
        """
        try:
            # Récupération de la configuration globale
            settings = get_settings()

            # Initialisation du nouveau client SDK Google GenAI
            self.client = genai.Client(api_key=api_key)

            # Si aucun modèle n'est fourni, on prend celui du config.py (Flash par défaut)
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL
            
            logger.debug(f"TriageAgent initialisé avec succès (Modèle: {self.model_name}).")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini : {e}")
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

            # 2. Appel à l'API Gemini en ASYNCHRONE avec .aio
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=IA_TriResponse,
                    temperature=0.1 
                )
            )

            # 3. Parsing de la réponse de l'IA
            ia_response = IA_TriResponse.model_validate_json(response.text)
            
            # 4. Assemblage sécurisé de l'objet métier final par le code Python
            decision = TriDecision(
                id_mail=mail.id_mail,
                **ia_response.model_dump() # On déverse les champs générés par l'IA
            )
            
            logger.info(
                f"Décision de tri prise [E-mail {decision.id_mail}] -> "
                f"Dossier: '{decision.dossier_cible}', "
                f"Priorité: '{decision.niveau_priorite.value}'"
            )
            
            return decision

        except ValidationError as e:
            logger.error(f"Erreur de validation Pydantic de la réponse IA pour l'e-mail {mail.id_mail} : {e}")
            raise AgentError(f"Le format renvoyé par l'IA ne correspond pas à TriDecision : {e}")
            
        except Exception as e:
            logger.error(f"Échec de l'évaluation asynchrone de l'e-mail {mail.id_mail} par l'IA : {e}")
            raise AgentError(f"Erreur lors de l'appel à l'API Gemini : {e}")