"""
Module des prompts (prompts)

Ce module centralise l'ensemble des instructions systémiques (System Prompts) 
et des modèles de requêtes (User Prompts) envoyés aux différents agents IA.
La séparation stricte de ces textes du reste du code facilite la maintenance 
et l'ajustement du comportement des modèles de langage.
"""

from .triage_prompts import get_triage_system_prompt
from .rag_prompts import get_rag_system_prompt, build_rag_user_prompt
from .synth_prompts import (
    get_pilotage_rewrite_prompt,
    get_main_courante_append_prompt,
    get_agenda_extraction_prompt
)