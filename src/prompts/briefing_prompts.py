from typing import List, Optional
from src.core import MailObject

def get_briefing_system_prompt() -> str:
    """
    Génère le prompt système pour l'agent de briefing (Gemini Flash).
    
    Définit le rôle de l'assistant : résumer de manière ultra-concise, professionnelle
    et structurée une liste d'e-mails pour une lecture rapide sur un écran de 
    smartphone (via Telegram).
    """
    return """Tu es un Secrétaire de Direction IA ultra-efficace, travaillant pour un Chef d'Établissement (Perdir).
Ta mission est de lire une liste d'e-mails bruts non lus et d'en faire un briefing de lecture rapide et percutant pour Telegram.

RÈGLES DE RÉDACTION STRICTES :
1. CONCISION EXTRÊME : Le chef d'établissement est pressé. Va droit au but. Ne fais pas de longues phrases.
2. FORMAT TELEGRAM (HTML) : Utilise des listes à puces (-) en début de ligne. Mets les éléments clés (noms, dates, sujets) en gras en utilisant STRICTEMENT les balises HTML <b>ton texte</b>. N'utilise jamais les astérisques (**).
3. ÉMOJIS UTILES : Utilise un (et un seul) émoji pertinent au début de chaque point pour catégoriser visuellement l'e-mail (ex: 🔴 pour urgent, 💶 pour finances, 👥 pour RH/Parents, 📅 pour agenda).
4. REGROUPEMENT : Si plusieurs e-mails parlent du même sujet, regroupe-les intelligemment dans un seul point.
5. TON : Professionnel, neutre et institutionnel.
6. INSTRUCTIONS SPÉCIFIQUES : Si l'utilisateur a donné une instruction de filtrage (ex: "Que les urgences"), tu DOIS ignorer tous les e-mails qui ne correspondent pas à ce critère. Si aucun e-mail ne correspond au critère, dis-le simplement de manière courtoise.
7. PAS DE BLA-BLA : Ne commence pas par "Voici votre résumé" et ne finis pas par "Avez-vous besoin d'autre chose ?". Renvoie UNIQUEMENT le contenu du briefing.
"""

def build_briefing_prompt(emails: List[MailObject], user_instruction: Optional[str] = None) -> str:
    """
    Construit le prompt utilisateur en agrégeant les métadonnées et le contenu 
    des e-mails à résumer.
    """
    prompt = ""
    
    # 1. Ajout de la consigne spécifique si elle existe
    if user_instruction and user_instruction.strip():
        prompt += f"ATTENTION - INSTRUCTION SPÉCIFIQUE DU CHEF D'ÉTABLISSEMENT : {user_instruction}\n"
        prompt += "Filtre et résume les e-mails ci-dessous UNIQUEMENT en fonction de cette instruction.\n\n"
    else:
        prompt += "Voici la liste des nouveaux e-mails à résumer :\n\n"

    # 2. Injection du contenu des e-mails
    for i, mail in enumerate(emails, 1):
        date_str = mail.date_reception.strftime("%d/%m/%Y à %H:%M")
        pj_str = f" [Pièces jointes : {', '.join(mail.pieces_jointes)}]" if mail.pieces_jointes else ""
        
        prompt += f"--- E-MAIL {i} ---\n"
        prompt += f"De : {mail.expediteur}\n"
        prompt += f"Date : {date_str}\n"
        prompt += f"Objet : {mail.sujet}{pj_str}\n"
        # On limite le contenu brut s'il est démesurément long (ex: > 3000 caractères)
        # pour ne pas noyer l'agent, bien que Flash gère de grands contextes.
        contenu = mail.contenu_texte[:3000] + ("..." if len(mail.contenu_texte) > 3000 else "")
        prompt += f"Contenu :\n{contenu}\n"
        prompt += "-" * 20 + "\n\n"

    return prompt