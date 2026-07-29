from typing import List, Optional
from google import genai
from google.genai import types

from src.core.models import MailObject
from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.utils.logger import get_logger

# Importation des constructeurs de prompts depuis le module dédié
from src.prompts.main_courante_prompts import (
    get_main_courante_system_prompt,
    build_main_courante_mail_prompt,
    build_main_courante_text_prompt
)

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class MainCouranteAgent:
    """
    Agent IA spécialisé dans la rédaction et le formatage des incidents 
    pour le journal de bord (Main Courante).
    Il intervient aussi bien de manière passive (Pipeline A - suite à un e-mail) 
    qu'active (Pipeline B - suite à un message Telegram).
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour la gestion de la main courante.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser (Gemini Flash recommandé).
        """
        try:
            # Récupération de la configuration globale
            settings = get_settings()

            # Initialisation du client SDK Google GenAI
            self.client = genai.Client(api_key=api_key)

            # Utilisation du modèle passé en paramètre ou celui par défaut (Flash est idéal ici)
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL
            
            logger.debug(f"MainCouranteAgent initialisé avec succès (Modèle: {self.model_name}).")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini : {e}")
            raise AgentError(f"Impossible d'initialiser l'Agent Main Courante : {e}")

    async def format_from_mail(self, mail: MailObject, existing_tags: Optional[List[str]] = None) -> str:
        """
        Analyse un e-mail contenant un événement sensible et génère une entrée factuelle, 
        professionnelle et balisée pour la Main Courante.

        Args:
            mail (MailObject): L'objet e-mail source contenant l'incident.
            existing_tags (Optional[List[str]]): Liste des tags (noms, types d'incidents) déjà utilisés 
                                                 dans le document pour favoriser la cohérence et 
                                                 éviter les doublons.

        Returns:
            str: La nouvelle entrée formatée en Markdown, prête à être ajoutée 
                 au fichier Main_Courante.md (Append).
        """
        logger.debug(f"Génération d'une entrée Main Courante à partir de l'e-mail ID: {mail.id_mail}")
        try:
            # Récupération des prompts
            system_prompt = get_main_courante_system_prompt()
            user_prompt = build_main_courante_mail_prompt(mail, existing_tags)

            # Appel asynchrone à l'API Gemini
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Température très basse (0.1) : on veut de la rigueur juridique et factuelle, 
                    # pas de créativité romancée pour une main courante d'établissement.
                    temperature=0.1, 
                )
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini est vide.")

            logger.info(f"Entrée Main Courante générée avec succès depuis l'e-mail {mail.id_mail}.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec de l'analyse factuelle de l'e-mail {mail.id_mail} : {e}")
            raise AgentError(f"Erreur lors du formatage Main Courante depuis un e-mail : {e}")


    async def format_from_text(self, raw_text: str, existing_tags: Optional[List[str]] = None) -> str:
        """
        Prend un compte-rendu brut dicté par le chef d'établissement via Telegram 
        et le reformate en un rapport d'incident neutre, factuel et structuré.

        Args:
            raw_text (str): Le texte brut ou la transcription vocale du Perdir.
            existing_tags (Optional[List[str]]): Liste des balises existantes pour harmoniser 
                                                 l'indexation.

        Returns:
            str: La nouvelle entrée formatée en Markdown, prête à être concaténée 
                 au fichier de suivi.
        """
        logger.debug("Génération d'une entrée Main Courante à partir d'un texte dicté/Telegram.")
        try:
            # Récupération des prompts
            system_prompt = get_main_courante_system_prompt()
            user_prompt = build_main_courante_text_prompt(raw_text, existing_tags)

            # Appel asynchrone à l'API Gemini
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Toujours une température très basse pour garantir le ton "Secrétariat de Direction"
                    temperature=0.1,
                )
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini est vide.")

            logger.info("Entrée Main Courante générée avec succès depuis le texte brut.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec du formatage Main Courante depuis le texte Telegram : {e}")
            raise AgentError(f"Erreur lors du formatage Main Courante depuis un texte : {e}")