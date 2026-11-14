from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)
STYLE_GUIDE_PATH = Path("data/style_perdir.md")

def get_draft_system_prompt() -> str:
    """
    Génère le prompt système pour l'Agent de rédaction.
    Tente de charger le guide de style local (Voice Card). Si le fichier 
    est absent, applique une dégradation gracieuse avec des règles génériques.
    """
    style_content = ""
    
    if STYLE_GUIDE_PATH.exists():
        try:
            with open(STYLE_GUIDE_PATH, "r", encoding="utf-8") as f:
                style_content = f.read()
            logger.debug("Guide de style (Voice Card) chargé avec succès pour le DraftAgent.")
        except Exception as e:
            logger.warning(f"Impossible de lire le fichier de style : {e}")

    if not style_content:
        # Solution de repli (Fallback) si le fichier est manquant
        style_content = (
            "Tu es l'assistant de rédaction du Principal du collège Xavier-Bichat.\n"
            "Rédige de manière très concise, professionnelle, sans jargon IA.\n"
            "Termine toujours par :\n"
            "Bien cordialement,\n\n"
            "HUGO JANIN\n"
            "Principal"
        )

    return (
        "Tu es un Agent IA spécialisé dans la rédaction de brouillons d'e-mails (DraftAgent).\n"
        "Ta mission est de rédiger le corps d'un e-mail en respectant STRICTEMENT l'intention "
        "fournie par l'Orchestrateur et en adoptant EXACTEMENT le style d'écriture défini ci-dessous.\n\n"
        "--- DÉBUT DU GUIDE DE STYLE (VOICE CARD) ---\n"
        f"{style_content}\n"
        "--- FIN DU GUIDE DE STYLE ---\n\n"
        "RÈGLE ABSOLUE : Ne génère AUCUN texte avant ou après l'e-mail (pas de 'Voici le brouillon'). "
        "Renvoie UNIQUEMENT le texte exact qui devra être inséré dans la boîte mail, incluant la signature."
    )

def build_draft_user_prompt(destinataire: str, sujet: str, contexte_original: str, directives_de_redaction: str) -> str:
    """
    Construit la requête contenant le contexte de l'e-mail à rédiger.
    """
    return (
        "Rédige le brouillon d'e-mail suivant en appliquant les règles de ton guide de style.\n\n"
        f"À : {destinataire}\n"
        f"Objet de l'e-mail : {sujet}\n"
        f"Contexte / E-mail précédent : {contexte_original}\n"
        f"Directives de rédaction (Ce que l'e-mail doit dire) : {directives_de_redaction}\n"
    )