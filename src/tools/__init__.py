"""
Module des outils (tools / Function Calling)

Ce module centralise l'ensemble des fonctions Python (les "bras robotiques") 
mises à la disposition de l'Agent Orchestrateur. 
Chaque outil est documenté via une docstring précise qui sert de "mode d'emploi" 
pour l'IA.
"""

# --- Outils de Messagerie (IMAP / ChromaDB) ---
from .mail_tools import (
    rechercher_dans_les_emails,
    enregistrer_brouillon_mail,
    generer_briefing_emails
)

# --- Outils Google Drive ---
from .drive_tools import (
    preparer_brouillon_main_courante,
    sauvegarder_main_courante_validee,
    rechercher_info_drive
)

# --- Outils d'Agenda et de Planification (Google Calendar / Tasks) ---
from .calendar_tools import (
    gerer_agenda,
    gerer_taches,
    programmer_alerte
)