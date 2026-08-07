import asyncio
from typing import Any, List
from google import genai
from google.genai import types

from src.core.config import get_settings
from src.core.dependencies import get_token_tracker_service
from src.core.exceptions import AgentError
from src.utils.logger import get_logger

logger = get_logger(__name__)

class GeminiRouterService:
    """
    Service centralisant les appels à l'API Gemini.
    Gère le routage (Flash vs Pro), le mécanisme de Fallback (Bascule automatique 
    sur compte payant en cas de quota gratuit dépassé) et le suivi des tokens.
    """

    def __init__(self) -> None:
        settings = get_settings()
        
        # Initialisation des deux clients
        self.client_free = genai.Client(api_key=settings.GEMINI_API_KEY_FREE)
        self.client_paid = genai.Client(api_key=settings.GEMINI_API_KEY_PAID)
        
        self.flash_lite_model = settings.GEMINI_FLASH_LITE_MODEL
        self.flash_model = settings.GEMINI_FLASH_MODEL
        self.pro_model = settings.GEMINI_PRO_MODEL
        
        logger.debug("GeminiRouterService initialisé avec les clients Gratuit et Payant.")

    async def _log_tokens(self, response: Any, model_name_logged: str, context: str) -> None:
        """Extrait les tokens de la réponse et les envoie au tracker."""
        tracker = get_token_tracker_service()
        if response.usage_metadata:
            in_t = response.usage_metadata.prompt_token_count or 0
            out_t = response.usage_metadata.candidates_token_count or 0
            if in_t > 0 or out_t > 0:
                await tracker.log_usage(model_name_logged, in_t, out_t, context)

    async def generate_content(
        self, 
        model_tier: str, 
        contents: Any, 
        config: types.GenerateContentConfig,
        action_context: str = "Inconnu"
    ) -> Any:
        """
        Exécute un prompt avec gestion du routage (Pro/Flash/Lite) et du Fallback (Gratuit/Payant).
        """
        # 1. Sélection du modèle exact selon la demande
        if model_tier.lower() == "pro":
            target_model = self.pro_model
        elif model_tier.lower() == "flash-lite":
            target_model = self.flash_lite_model
        else:
            target_model = self.flash_model

        # 2. Mécanique de facturation et de Fallback
        if model_tier.lower() == "pro":
            logger.debug(f"[{action_context}] Routage vers {target_model} (Payant forcé).")
            response = await self.client_paid.aio.models.generate_content(
                model=target_model, contents=contents, config=config
            )
            await self._log_tokens(response, "pro_payant", action_context)
            return response
            
        else:
            # Pour "flash" et "flash-lite", on tente d'abord le gratuit
            tier_name = model_tier.lower() 
            try:
                logger.debug(f"[{action_context}] Routage vers {target_model} (Gratuit)...")
                response = await self.client_free.aio.models.generate_content(
                    model=target_model, contents=contents, config=config
                )
                await self._log_tokens(response, f"{tier_name}_gratuit", action_context)
                return response
                
            except Exception as e:
                error_msg = str(e).lower()
                # On attrape les quotas (429) ET les surcharges serveurs Google (503, 500)
                if any(kw in error_msg for kw in ["429", "quota", "503", "500", "overloaded", "high demand"]):
                    logger.warning(f"[{action_context}] API Gratuite saturée ou quota dépassé. BASCULE sur {target_model} (Payant).")
                    
                    response = await self.client_paid.aio.models.generate_content(
                        model=target_model, contents=contents, config=config
                    )
                    await self._log_tokens(response, f"{tier_name}_payant", action_context)
                    return response
                else:
                    raise AgentError(f"Erreur API Gemini : {e}")

    async def send_chat_message(
        self,
        model_tier: str,
        history: List[types.Content],
        user_message: str,
        config: types.GenerateContentConfig,
        action_context: str = "Orchestrateur"
    ) -> Any:
        """
        Spécifique pour l'Orchestrateur (Pipeline B) qui utilise une session de Chat 
        pour maintenir le contexte et utiliser le Function Calling (Outils).
        """
        # Résolution du modèle selon le paramètre
        if model_tier.lower() == "pro":
            target_model = self.pro_model
        elif model_tier.lower() == "flash-lite":
            target_model = self.flash_lite_model
        else:
            target_model = self.flash_model

        try:
            # On tente d'abord en gratuit avec le modèle ciblé
            chat_free = self.client_free.aio.chats.create(
                model=target_model, history=history, config=config
            )
            response = await chat_free.send_message(user_message)
            await self._log_tokens(response, f"{model_tier.lower()}_gratuit", action_context)
            return response
            
        except Exception as e:
            error_msg = str(e).lower()
            if any(kw in error_msg for kw in ["429", "quota", "503", "500", "overloaded", "high demand"]):
                logger.warning(f"[{action_context}] API Gratuite saturée (Chat). BASCULE sur compte Payant.")
                
                # On recrée la session de chat avec le client payant
                chat_paid = self.client_paid.aio.chats.create(
                    model=target_model, history=history, config=config
                )
                response = await chat_paid.send_message(user_message)
                await self._log_tokens(response, f"{model_tier.lower()}_payant", action_context)
                return response
            else:
                raise AgentError(f"Erreur API Gemini (Chat) : {e}")