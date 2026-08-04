from typing import Optional
from google import genai
from google.genai import types

from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.utils.logger import get_logger

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
    de la journée et mettre à jour rigoureusement le fichier Markdown "Mémoire de l'Établissement".
    """

    def __init__(self, api_key: str, model_name: Optional[str] = None) -> None:
        """
        Initialise le client de l'API Gemini pour les tâches de synthèse complexes.

        Args:
            api_key (str): La clé API Google Gemini.
            model_name (Optional[str]): Le nom du modèle à utiliser (Gemini Pro recommandé).
        """
        try:
            settings = get_settings()
            self.client = genai.Client(api_key=api_key)
            
            # Utilisation de Gemini Pro par défaut pour sa capacité de raisonnement (fenêtre de contexte large)
            #self.model_name = model_name or settings.GEMINI_PRO_MODEL
            self.model_name = model_name or settings.GEMINI_FLASH_MODEL #Flash pour les tests
            
            logger.debug(f"SynthAgent initialisé avec succès (Modèle: {self.model_name}).")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Gemini (Synthèse) : {e}")
            raise AgentError(f"Impossible d'initialiser l'Agent de Synthèse : {e}")

    async def rewrite_memoire_etablissement_content(self, current_markdown: str, daily_info: str) -> Optional[str]:
        """
        Applique la mécanique "Read-Rewrite-Replace" pour le fichier de mémoire.
        Évalue l'impact des nouvelles informations de la journée (mails + notes Telegram), 
        fusionne intelligemment les données dans les rubriques concernées du Markdown 
        sans altérer sa structure.

        Args:
            current_markdown (str): Le contenu intégral actuel du fichier.
            daily_info (str): Le texte consolidé contenant tous les événements de la journée.

        Returns:
            Optional[str]: Le nouveau contenu Markdown complet, prêt à écraser l'ancien fichier, 
                           ou None si l'API échoue.
        """
        logger.info("Début de l'analyse et de la réécriture de la Mémoire de l'Établissement par l'IA.")
        
        try:
            # 1. Préparation des prompts
            system_prompt = get_pilotage_system_prompt()
            user_prompt = build_pilotage_update_prompt(current_markdown, daily_info)

            # 2. Appel asynchrone à l'API Gemini Pro
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    # Température très basse (0.1) : On exige de la rigueur structurelle (Markdown),
                    # l'IA ne doit faire preuve d'aucune créativité littéraire ici.
                    temperature=0.1, 
                )
            )

            if not response.text:
                raise AgentError("La réponse générée par Gemini (SynthAgent) est vide.")

            # 3. Nettoyage de sécurité supplémentaire
            # Au cas où le LLM ajouterait quand même des balises malgré l'interdiction du prompt
            final_text = response.text.strip()
            if final_text.startswith("```markdown"):
                final_text = final_text[11:]
            if final_text.startswith("```"):
                final_text = final_text[3:]
            if final_text.endswith("```"):
                final_text = final_text[:-3]

            logger.info("Réécriture de la Mémoire de l'Établissement générée avec succès.")
            return final_text.strip()

        except Exception as e:
            logger.error(f"Échec lors de la réécriture du document par l'Agent de Synthèse : {e}", exc_info=True)
            return None

    async def generate_update_summary(self, old_markdown: str, new_markdown: str) -> str:
        """
        Génère un résumé des modifications apportées (ajouts, suppressions) au fichier 
        Mémoire, destiné à être envoyé au Perdir via Telegram.

        Args:
            old_markdown (str): L'ancienne version du fichier.
            new_markdown (str): La nouvelle version du fichier.
            
        Returns:
            str: Un résumé concis des changements (format HTML pour Telegram).
        """
        logger.debug("Génération du résumé des modifications pour Telegram...")
        
        try:
            # Création du contexte comparatif à envoyer au modèle
            changes_diff = (
                "--- ANCIENNE VERSION ---\n"
                f"{old_markdown}\n\n"
                "--- NOUVELLE VERSION ---\n"
                f"{new_markdown}"
            )
            
            # Récupération du prompt dédié au résumé
            user_prompt = build_summary_prompt(changes_diff)

            # Appel asynchrone (On peut utiliser Gemini Flash ici pour aller plus vite,
            # mais on garde le Pro instancié par simplicité et cohérence).
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    # Température légèrement plus haute (0.3) pour un ton plus naturel dans le résumé
                    temperature=0.3, 
                )
            )

            if not response.text:
                logger.warning("Le résumé généré est vide, renvoi d'un message par défaut.")
                return "La mémoire de l'établissement a été mise à jour, mais le résumé n'a pas pu être généré."

            logger.info("Résumé de synthèse généré avec succès.")
            return response.text.strip()

        except Exception as e:
            logger.error(f"Échec lors de la génération du résumé de synthèse : {e}")
            return "✅ La Mémoire de l'Établissement a bien été mise à jour (le résumé textuel est indisponible suite à une erreur technique)."