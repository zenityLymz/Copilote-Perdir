"""
Module d'orchestration (workflows)

Ce module contient les classes de haut niveau qui orchestrent les processus métiers.
Les workflows n'implémentent pas de logique d'API directe, mais coordonnent 
l'interaction entre les services (IMAP, Drive, Telegram) et les agents IA.
"""

from .mail_pipeline import MailPipeline
from .reporting import ReportingWorkflow
from .strategic_memory import StrategicMemoryWorkflow