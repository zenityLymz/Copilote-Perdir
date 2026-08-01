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
    ajouter_main_courante,
    rechercher_document_drive
)

# --- Outils d'Agenda et de Planification (Google Calendar / Tasks) ---
from .calendar_tools import (
    creer_evenement_agenda,
    creer_tache,
    programmer_alerte
)