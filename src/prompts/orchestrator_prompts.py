from datetime import datetime
from typing import Optional, List

def get_orchestrator_system_prompt() -> str:
    """
    Génère le prompt système définissant le rôle, le ton et les règles de 
    comportement de l'Agent Orchestrateur (le "Cerveau" du système).
    
    Returns:
        str: Le prompt système complet.
    """
    return """Tu es le "Copilote", l'assistant IA exclusif et proactif d'un Chef d'Établissement (Perdir) de l'Éducation Nationale française.
Ton objectif principal est d'alléger sa charge mentale au quotidien en organisant l'information et en exécutant des tâches administratives.

RÈGLES DE COMPORTEMENT STRICTES :

1. INTERLOCUTEUR UNIQUE : Tu es la seule interface entre le système technique et le chef d'établissement. Tes réponses doivent être naturelles, humaines et masquer la complexité technique des outils sous-jacents.
2. TON ET STYLE : Sois toujours professionnel, courtois, clair et extrêmement concis. Le Perdir manque de temps, va directement à l'essentiel.
3. BOÎTE À OUTILS (FUNCTION CALLING) : Tu disposes d'outils pour lire des documents, chercher des e-mails, gérer l'agenda et créer des brouillons. Utilise-les de manière autonome dès que cela est pertinent pour répondre à la demande.
4. RAISONNEMENT ET CLARIFICATION : Si l'utilisateur te donne un ordre (ex: "Mets un rendez-vous avec le maire demain") mais qu'il manque un paramètre essentiel pour utiliser ton outil (ex: l'heure exacte), NE DEVINE JAMAIS. Pose une question courte et directe à l'utilisateur pour obtenir l'information manquante avant d'agir.
5. CONTEXTE ET MÉMOIRE : Appuie-toi sur l'historique récent de la conversation pour comprendre les sous-entendus.
6. GESTION DES ÉCHECS : Si un outil technique échoue ou si tu n'as pas accès à une information, excuse-toi poliment, explique brièvement le problème et propose éventuellement une alternative. N'invente jamais d'informations (zéro hallucination).
"""

def build_orchestrator_prompt(user_message: str, system_alerts: Optional[List[str]] = None) -> str:
    """
    Construit le prompt dynamique injecté à l'Agent Orchestrateur à chaque tour de parole.
    
    Cette fonction encapsule la requête de l'utilisateur avec des métadonnées vitales 
    (comme l'horodatage exact et l'état des services) pour ancrer l'IA dans la réalité 
    temporelle et technique avant qu'elle ne prenne une décision.
    
    Args:
        user_message (str): Le message brut envoyé par le chef d'établissement via Telegram.
        system_alerts (Optional[List[str]]): Une liste optionnelle d'alertes techniques 
                                             provenant des services (ex: ["Drive indisponible", 
                                             "IMAP hors ligne"]).
                                             
    Returns:
        str: Le prompt formaté combinant le contexte dynamique et la demande de l'utilisateur.
    """
    # Récupération de la date et de l'heure actuelles (crucial pour le Function Calling d'agenda)
    now = datetime.now()
    
    # Formatage de la date (ex: "vendredi 31 juillet 2026 à 16:52")
    # Il peut être utile de forcer la locale en français (locale.setlocale) selon l'environnement
    current_time_str = now.strftime("%A %d %B %Y à %H:%M")
    
    # Formatage des alertes système s'il y en a (Dégradation gracieuse)
    alerts_section = ""
    if system_alerts and len(system_alerts) > 0:
        alerts_formatted = "\n- ".join(system_alerts)
        alerts_section = (
            f"\n\n[ÉTAT DU SYSTÈME : Attention, des défaillances techniques sont en cours :\n"
            f"- {alerts_formatted}\n"
            f"Adapte tes réponses en conséquence, excuse-toi si nécessaire, et ne tente pas "
            f"d'utiliser les outils liés à ces services.]"
        )
        
    # Construction du prompt final
    prompt = (
        f"[CONTEXTE TEMPOREL ET TECHNIQUE]\n"
        f"Date et heure actuelles : {current_time_str}{alerts_section}\n\n"
        f"[NOUVEAU MESSAGE DU CHEF D'ÉTABLISSEMENT]\n"
        f"{user_message}"
    )
    
    return prompt