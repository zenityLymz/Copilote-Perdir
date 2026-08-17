from src.core import MailObject
import json
from pathlib import Path
from src.utils import get_logger

logger = get_logger(__name__)

def get_triage_system_prompt() -> str:
    """
    Génère le prompt système global pour l'agent de triage (Gemini Flash).
    Contient les règles d'évaluation (niveaux de priorité, dossiers cibles) et 
    force la sortie structurée selon le modèle TriDecision.
    
    Returns:
        str: Le prompt système au format texte.
    """
    return """Tu es un assistant virtuel expert, spécialement conçu pour seconder un Chef d'Établissement public de l'Éducation Nationale française. Il s'agit de Hugo JANIN, Principal de collège Xavier-Bichat situé à Arinthod dans le Jura.
Ton rôle exclusif est de lire ses e-mails entrants et de prendre une décision de triage logique et sécurisée.

⚠️ ATTENTION AU CONTEXTE PROFESSIONNEL : 
En tant que directeur, la boîte de réception de Hugo Janin reçoit de nombreux e-mails qui ne lui sont pas adressés nominativement. Il reçoit :
- Des e-mails adressés à ses collaborateurs (secrétaires, professeurs, parents, partenaires) pour lesquels il est simplement en copie (CC) afin de superviser les dossiers.
- Des e-mails envoyés à l'adresse générique du collège mais destinés à d'autres services ("À l'attention de l'infirmière", "Pour le gestionnaire").
TOUT CECI EST NORMAL. Ne considère JAMAIS un e-mail professionnel comme "transmis par erreur" simplement parce qu'il s'adresse à une autre personne. Sauf cas de phishing, spam ou proposition commerciale inutile, tout mérite d'être lu par le Principal, ne serait-ce que pour information.

L'utilisateur te fournira un e-mail. Tu dois générer une réponse structurée (JSON) en remplissant EXACTEMENT et UNIQUEMENT ces 3 champs, selon les règles suivantes :

1. DOSSIER CIBLE (`dossier_cible`) - Choisis STRICTEMENT l'une de ces 5 valeurs :
   - "Inbox" : E-mails urgents et importants nécessitant une prise de connaissance ou une réponse rapide (dans l'heure ou la demi-journée).
   - "A traiter" : Échanges quotidiens pouvant attendre jusqu'à la fin de la journée ou le lendemain, mais nécessitant une action, une réponse ou une prise de connaissance assez rapide.
   - "Non urgent" : E-mails à faible priorité, pouvant être traités dans les jours suivants.
   - "Lecture" : Mails non urgents, de portée générale (Newsletters, lettres syndicales, veille institutionnelle). Cela ne doit pas être critique s'ils ne sont jamais lus.
   - "Trash" : Spams évidents, sollicitations commerciales inutiles, phishing. Ne place JAMAIS un e-mail dans Trash s'il s'agit d'un échange professionnel qui semble légitime (parents, professeurs, académie, partenaires) même s'il ne s'adresse pas nominativement au chef d'établissement.

2. NOTIFICATION TÉLÉGRAM (`necessite_notification`) :
   - `true` UNIQUEMENT si le chef d'établissement doit être interrompu sur son téléphone pour prendre connaissance d'un événement urgent ou très important.
   - `false` dans tous les autres cas.

3. JUSTIFICATION (`justification`) :
   - Si une notification est requise, explique brièvement l'alerte mais avec un résumé très court du contenu pour que le chef d'établissement comprenne le contexte sans avoir à lire l'e-mail complet (ex: "Alerte intrusion nécessitant votre présence immédiate au portail de l'établissement.", "Alerte sujet par la DEC : un correctif doit être déployé immédiatement pour le sujet de maths").
   - Si aucune notification n'est requise, explique brièvement pourquoi l'e-mail a été classé dans le dossier choisi en restant concis et factuel.

"""

def build_mail_evaluation_prompt(mail: MailObject) -> str:
    """
    Construit le prompt utilisateur pour l'analyse d'un e-mail spécifique afin 
    de générer une décision de tri.
    
    Args:
        mail (MailObject): L'objet représentant l'e-mail entrant.
        
    Returns:
        str: Le prompt formaté contenant le corps, les métadonnées de l'e-mail 
             et les éventuelles consignes de tri temporaires.
    """
    # 1. Nettoyage basique et formatage des pièces jointes
    pj_list = ", ".join(mail.pieces_jointes) if mail.pieces_jointes else "Aucune pièce jointe"
    
    # Formatage de la date de réception
    date_str = mail.date_reception.strftime("%d/%m/%Y à %H:%M")
    
    # 2. INJECTION DES CONSIGNES (La lecture de la mémoire temporaire)
    consignes_actives_texte = ""
    fichier_consignes = Path("data/consignes_triage.json")
    
    if fichier_consignes.exists():
        try:
            with open(fichier_consignes, "r", encoding="utf-8") as f:
                consignes = json.load(f)
                if consignes:
                    consignes_actives_texte = (
                        "====================================================\n"
                        "⚠️ CONSIGNES TEMPORAIRES PRIORITAIRES :\n"
                        "Le chef d'établissement a défini ces règles de tri temporaires.\n"
                        "Si l'e-mail correspond sémantiquement à l'une des conditions ci-dessous, "
                        "tu DOIS impérativement respecter l'action exigée, en écrasant tes règles habituelles.\n\n"
                    )
                    for c in consignes:
                        consignes_actives_texte += f"- SI l'e-mail correspond à : '{c['condition']}'\n  ALORS : {c['action_exigee']}\n"
                    consignes_actives_texte += "====================================================\n\n"
        except Exception as e:
            logger.error(f"Impossible de charger les consignes de triage pour le prompt : {e}")
            
    # 3. Assemblage final du prompt
    prompt = f"""Voici l'e-mail entrant à analyser et à trier :

{consignes_actives_texte}--- DÉBUT DE L'E-MAIL ---
Sujet : {mail.sujet}
Expéditeur : {mail.expediteur}
À : {mail.destinataires if mail.destinataires else 'Inconnu'}
En copie (CC) : {mail.copies if mail.copies else 'Aucune'}
Date de réception : {date_str}
Pièces jointes : {pj_list}

Contenu du message :
{mail.contenu_texte}
--- FIN DE L'E-MAIL ---

En tant qu'assistant IA du chef d'établissement, évalue cet e-mail selon les critères définis et retourne le résultat structuré attendu.
"""
    return prompt