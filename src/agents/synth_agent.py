from typing import Optional
from google import genai
from google.genai import types

from src.core.exceptions import AgentError
from src.utils.logger import get_logger
from src.core.dependencies import get_gemini_router_service

# Importation des constructeurs de prompts mis à jour
from src.prompts.synth_prompts import (
    get_pilotage_system_prompt,
    build_pilotage_update_prompt,
    build_summary_prompt
)

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class SynthAgent:
    """
    Agent IA spécialisé dans l'analyse stratégique complexe et la structuration de textes.
    Intervient exclusivement dans le Pipeline C (traitement différé du soir).
    Utilise le modèle avancé (Gemini Pro) pour analyser l'impact des informations 
    de la journée et mettre à jour rigoureusement le fichier html "Mémoire de l'Établissement".
    """

    def __init__(self) -> None:
        """
        Initialise le client de l'API Gemini pour les tâches de synthèse complexes.

        """
        try:
            self.router = get_gemini_router_service()
            
            logger.debug(f"SynthAgent initialisé avec succès via GeminiRouterService.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini (Synthèse) : {e}")
            raise AgentError(f"Impossible d'initialiser l'Agent de Synthèse : {e}")

    async def rewrite_memoire_etablissement_content(self, current_html: str, daily_info: str) -> Optional[str]:
        """
        Applique la mécanique "Read-Rewrite-Replace" pour le fichier de mémoire.
        Évalue l'impact des nouvelles informations de la journée (mails + notes Telegram), 
        fusionne intelligemment les données dans les rubriques concernées sans altérer sa structure.

        Args:
            current_html (str): Le contenu intégral actuel du fichier.
            daily_info (str): Le texte consolidé contenant tous les événements de la journée.

        Returns:
            Optional[str]: Le nouveau contenu html complet, prêt à écraser l'ancien fichier, 
                           ou None si l'API échoue.
        """
        logger.info("Début de l'analyse et de la réécriture de la Mémoire de l'Établissement par l'IA.")
        
        try:
            # 1. Préparation des prompts
            system_prompt = get_pilotage_system_prompt()
            user_prompt = build_pilotage_update_prompt(current_html, daily_info)

            # 2. Appel asynchrone à l'API Gemini Pro
            response = await self.router.generate_content(
                model_tier="pro",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Température très basse (0.1) : On exige de la rigueur structurelle (html),
                    # l'IA ne doit faire preuve d'aucune créativité littéraire ici.
                    temperature=0.1, 
                ),
                action_context="Synthese_Nocturne_PRO"
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini (SynthAgent) est vide.")

            # Nettoyage de sécurité adapté au HTML
            final_text = response.text.strip()
            if final_text.startswith("```html"):
                final_text = final_text[7:]
            if final_text.startswith("```"):
                final_text = final_text[3:]
            if final_text.endswith("```"):
                final_text = final_text[:-3]

            logger.info("Réécriture de la Mémoire de l'Établissement générée avec succès.")
            return final_text.strip()

        except Exception as e:
            logger.error(f"Échec lors de la réécriture du document par l'Agent de Synthèse : {e}", exc_info=True)
            return None

    async def generate_update_summary(self, old_html: str, new_html: str) -> str:
        """
        Génère un résumé des modifications apportées (ajouts, suppressions) au fichier 
        Mémoire, destiné à être envoyé au Perdir via Telegram.

        Args:
            old_html (str): L'ancienne version du fichier.
            new_html (str): La nouvelle version du fichier.
            
        Returns:
            str: Un résumé concis des changements (format HTML pour Telegram).
        """
        logger.debug("Génération du résumé des modifications pour Telegram...")
        
        try:
            # Création du contexte comparatif à envoyer au modèle
            changes_diff = (
                "--- ANCIENNE VERSION ---\n"
                f"{old_html}\n\n"
                "--- NOUVELLE VERSION ---\n"
                f"{new_html}"
            )
            
            # Récupération du prompt dédié au résumé
            user_prompt = build_summary_prompt(changes_diff)

            # On bascule sur le modèle FLASH pour le résumé simple
            response = await self.router.generate_content(
                model_tier="flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    # Température légèrement plus haute (0.3) pour un ton plus naturel dans le résumé
                    temperature=0.3, 
                ),
                action_context="Synthese_Resume_Telegram"
            )

            if not response.text:
                logger.warning("Le résumé généré est vide, renvoi d'un message par défaut.")
                return "La mémoire de l'établissement a été mise à jour, mais le résumé n'a pas pu être généré."

            logger.info("Résumé de synthèse généré avec succès.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec lors de la génération du résumé de synthèse : {e}")
            return "✅ La Mémoire de l'Établissement a bien été mise à jour (le résumé textuel est indisponible suite à une erreur technique)."