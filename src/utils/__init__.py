"""
Module utilitaire (utils)

Ce module expose les fonctions transverses de l'application, notamment
la configuration de la journalisation (logging) et les outils de traitement
de texte nécessaires pour la préparation des données avant l'envoi aux LLMs.
"""

from .logger import setup_logger, get_logger
from .text_utils import (
    clean_html_content,
    estimate_token_count,
    truncate_text_for_llm,
    sanitize_filename,
    extract_email_address
)