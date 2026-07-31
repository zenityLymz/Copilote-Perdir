from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode


from src.utils.logger import get_logger


# Initialisation du logger
logger = get_logger(__name__)

class PipelineBTelegram:
    """
    Orchestrateur du Pipeline B (Actif) : Assistant Interactif Telegram.
    
    Ce workflow est déclenché par la réception d'un message (texte ou audio) 
    du chef d'établissement. Il délègue la compréhension de l'intention à 
    l'OrchestratorAgent.
    """


