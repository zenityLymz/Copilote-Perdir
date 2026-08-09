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
from .synth_prompts import (
    get_hebdo_synthesis_system_prompt,
    build_hebdo_synthesis_prompt
)
from .briefing_prompts import (
    get_briefing_system_prompt,
    build_briefing_prompt
)
from .main_courante_prompts import (
    get_main_courante_system_prompt,
    build_main_courante_text_prompt
)
from .orchestrator_prompts import (
    get_orchestrator_system_prompt,
    build_orchestrator_prompt
)