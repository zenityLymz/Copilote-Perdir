"""
Module des prompts (prompts)

Ce module centralise l'ensemble des instructions systémiques (System Prompts) 
et des modèles de requêtes (User Prompts) envoyés aux différents agents IA.
La séparation stricte de ces textes du reste du code facilite la maintenance 
et l'ajustement du comportement des modèles de langage.
"""

from .triage_prompts import (
    get_triage_system_prompt,
    build_mail_evaluation_prompt
)
from .rag_prompts import (
    get_rag_system_prompt,
    build_rag_qa_prompt
)
from .synth_prompts import (
    get_pilotage_system_prompt,
    build_pilotage_update_prompt,
    build_summary_prompt
)
from .router_prompts import (
    get_router_system_prompt,
    build_router_prompt
)
from .briefing_prompts import (
    get_briefing_system_prompt,
    build_briefing_prompt
)
from .main_courante_prompts import (
    get_main_courante_system_prompt,
    build_main_courante_mail_prompt,
    build_main_courante_text_prompt
)