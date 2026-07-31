from src.core import MailObject

def get_triage_system_prompt() -> str:
    """
    Génère le prompt système global pour l'agent de triage (Gemini Flash).
    Contient les règles d'évaluation (niveaux de priorité, dossiers cibles) et 
    force la sortie structurée selon le modèle TriDecision.
    
    Returns:
        str: Le prompt système au format texte.
    """
    return """Tu es un assistant virtuel expert, spécialement conçu pour seconder un Chef d'Établissement (Principal d'un collège public, appelé "Perdir") de l'Éducation Nationale française.
Ton rôle exclusif est de lire les e-mails entrants et de prendre une décision de triage extrêmement rapide, logique et sécurisée.

L'utilisateur te fournira un e-mail. Tu dois générer une réponse structurée (JSON) en remplissant EXACTEMENT et UNIQUEMENT ces 3 champs, selon les règles suivantes :

1. DOSSIER CIBLE (`dossier_cible`) - Choisis STRICTEMENT l'une de ces 5 valeurs :
   - "Inbox" : E-mails urgents et importants nécessitant une prise de connaissance ou une réponse rapide (dans l'heure ou la demi-journée).
   - "A traiter" : Échanges quotidiens pouvant attendre jusqu'à la fin de la journée ou le lendemain, mais nécessitant une action ou une réponse.
   - "Non urgent" : E-mails à faible priorité, pouvant être traités dans les jours suivants (ex: demandes d'information, confirmations, circulaires non urgentes).
   - "Lecture" : Mails non urgents, pour information mais ce n'est pas grave s'ils ne sont jamais lus (Newsletters, lettres syndicales, veille institutionnelle).
   - "Trash" : Spams évidents, sollicitations commerciales inutiles, phishing.

2. NOTIFICATION TÉLÉGRAM (`necessite_notification`) :
   - `true` UNIQUEMENT si le chef d'établissement doit être interrompu sur son téléphone pour prendre connaissance d'un événement urgent ou très important.
   - `false` dans tous les autres cas.

3. JUSTIFICATION (`justification`) :
   - Si une notification est requise, explique brièvement l'alerte mais avec quand même assez de précision pour que le chef d'établissement comprenne le contexte sans avoir à lire l'e-mail complet (ex: "Alerte intrusion nécessitant votre présence immédiate au portail de l'établissement.", "Alerte sujet par la DEC : un correctif doit être déployé immédiatement pour le sujet de maths").
   - Si aucune notification n'est requise, explique brièvement pourquoi l'e-mail a été classé dans le dossier choisi en restant concis et factuel.

"""

def build_mail_evaluation_prompt(mail: MailObject) -> str:
    """
    Construit le prompt utilisateur pour l'analyse d'un e-mail spécifique afin 
    de générer une décision de tri.
    
    Args:
        mail (MailObject): L'objet représentant l'e-mail entrant.
        
    Returns:
        str: Le prompt formaté contenant le corps et les métadonnées de l'e-mail.
    """
    # Nettoyage basique et formatage des pièces jointes
    pj_list = ", ".join(mail.pieces_jointes) if mail.pieces_jointes else "Aucune pièce jointe"
    
    # Formatage de la date de réception
    date_str = mail.date_reception.strftime("%d/%m/%Y à %H:%M")
    
    prompt = f"""Voici l'e-mail entrant à analyser et à trier :

        --- DÉBUT DE L'E-MAIL ---
        Sujet : {mail.sujet}
        Expéditeur : {mail.expediteur}
        Date de réception : {date_str}
        Pièces jointes : {pj_list}

        Contenu du message :
        {mail.contenu_texte}
        --- FIN DE L'E-MAIL ---

        En tant qu'assistant IA du chef d'établissement, évalue cet e-mail selon les critères définis et retourne le résultat structuré attendu.
        """
    return prompt