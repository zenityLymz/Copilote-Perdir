"""
Module des agents IA (agents)

Ce module contient les classes responsables de l'interaction directe avec 
les modèles de langage (LLMs) de l'API Google Gemini. Chaque agent a une 
spécialité métier distincte et utilise des prompts spécifiques.
"""

from .triage_agent import TriageAgent
from .synth_agent import SynthAgent
from .orchestrator_agent import OrchestratorAgent
from .briefing_agent import BriefingAgent
from .main_courante_agent import MainCouranteAgent