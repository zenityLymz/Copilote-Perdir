"""
Module d'orchestration (workflows)

Ce module contient les classes de haut niveau qui orchestrent les processus métiers 
répartis en trois pipelines distincts (Passif, Actif, Différé).
Les workflows n'implémentent pas de logique d'API directe, mais coordonnent 
l'interaction entre les services (IMAP, Drive, Telegram) et les agents IA.
"""

from .pipeline_a_mails import PipelineAMails
from .pipeline_b_telegram import PipelineBTelegram