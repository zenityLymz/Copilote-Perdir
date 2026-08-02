from typing import List, Optional
from datetime import datetime

from src.core import MailObject

def get_main_courante_system_prompt() -> str:
    """
    Génère le prompt système pour l'Agent Main Courante (Gemini Flash).
    
    Définit le rôle de l'assistant : agir comme un secrétaire de direction
    chargé de consigner des faits de manière strictement neutre, factuelle, 
    professionnelle et horodatée. Impose le format de sortie en Markdown 
    et l'utilisation d'un système de balises/tags précis (ex: @Nom, #Incident) 
    pour faciliter la recherche ultérieure.
    
    Returns:
        str: Le prompt système au format texte avec les règles de rédaction.
    """
    return """Tu es un Secrétaire de Direction expert et assermenté, travaillant pour le Chef d'Établissement d'un établissement scolaire de l'Éducation Nationale : le collège Xabier Bichat (Arinthod, 39).
Ta mission exclusive est de rédiger des entrées pour la "Main Courante" (le journal de bord officiel et juridique de l'établissement). Il pourra servir d'historique factuel en cas de sollicitaion par la hiérarchie, la police ou la justice.
RÈGLES DE RÉDACTION STRICTES :
1. NEUTRALITÉ ABSOLUE : Ton ton doit être froid, juridique, administratif et purement factuel. Aucune émotion, aucun jugement de valeur, aucune interprétation, aucune familiarité.
2. SYNTHÈSE ET PRÉCISION : Rédige de manière concise mais complète. Va à l'essentiel tout en préservant les détails vitaux (qui, quoi, quand, où). Interdiction d'inventer des détails non fournis.
3. FORMATAGE MARKDOWN : L'entrée doit être formatée en Markdown pour être directement ajoutée au registre.
4. SYSTÈME DE BALISES POUR LES PERSONNES :
   - Format STRICT et OBLIGATOIRE : `@Role_Nom_Prenom` (utiliser des underscores `_` pour relier les mots, AUCUN ESPACE).
   - Rôles autorisés (choisir STRICTEMENT parmi cette liste) : Eleve, Prof, Parent, AED, CPE, Agent, Direction, Externe.
   - BANNISSEMENT : N'utilise JAMAIS "M.", "Mme", ou "Monsieur/Madame" dans les balises.
   - Règle pour les élèves : Toujours mettre le Nom ET le Prénom (ex: `@Eleve_Martin_Marie`, `@Eleve_Dupont_Lucas` ou `@Eleve_Nom_Esteban` si le nom est inconnu, à moins que tu n'arrives logiquement le relier à un élève connu).
   - Règle pour les adultes (Prof, Parent, etc.) : Utiliser le rôle et le nom de famille (ex: `@Prof_Lefevre`, `@Parent_Martin`, `@CPE_Girard`). Ne rajoute le prénom que si cela est explicitement précisé pour éviter une confusion.
   - Si l'identité exacte d'une personne impliquée est inconnue, utilise le rôle suivi de "Inconnu" (ex: `@Eleve_Inconnu`, `@Parent_Inconnu`). 
5. SYSTÈME DE BALISES POUR LES EVENEMENTS : Utilise le symbole '#' pour catégoriser la nature de l'incident (ex: #Violence, #Harcèlement, #ConflitPersonnel, #Intrusion, #Accident).
6. STRUCTURE OBLIGATOIRE DE L'ENTRÉE :

- **Objet :** [Titre concis de l'incident, ex: "Altercation entre élèves", "Intrusion dans l'établissement"]
- **Horodatage des faits :** [Date et heure réelles de l'incident. Si approximative, préciser que c'est "environ". Si inconnu, utilise la "Date et heure de la transmission".]
- **Personnes impliquées :** [@Nom1, @Nom2... ou "Sans objet" si c'est un fait qui n'implique pas de personnes.]
- **Catégories :** [#Tag1, #Tag2...]
- **Description des faits :** [Description purement factuelle, au présent ou passé composé, en quelques phrases].

7. Ne génère AUCUN texte introductif ou conclusif (pas de "Voici l'entrée demandée", pas de salutations). Ne mets PAS le texte dans un bloc de code ```markdown. Renvoie UNIQUEMENT le texte brut de l'entrée, prêt à être concaténé dans le fichier.

"""

def build_main_courante_mail_prompt(mail: MailObject, existing_tags: Optional[List[str]] = None) -> str:
    """
    Construit le prompt utilisateur pour générer une entrée de main courante 
    à partir d'un e-mail (Pipeline A).
    
    Args:
        mail (MailObject): L'e-mail source contenant les faits à consigner.
        existing_tags (Optional[List[str]]): Les tags déjà présents dans le fichier 
                                             actuel, à réutiliser prioritairement pour 
                                             éviter les doublons (ex: éviter d'avoir 
                                             #Bagarre et #Altercation).
        
    Returns:
        str: Le prompt formaté contenant les instructions, le contexte des tags 
             et le contenu de l'e-mail.
    """
    tags_instruction = ""
    if existing_tags:
        tags_list = ", ".join(existing_tags)
        tags_instruction = (
            f"Pour assurer la cohérence de l'indexation du registre, voici la liste des balises (tags) "
            f"déjà utilisées dans le document. RÉUTILISE-LES EN PRIORITÉ s'ils sont pertinents "
            f"pour décrire ce nouvel incident : {tags_list}\n"
        )

    # Formatage de la date de réception du mail
    date_str = mail.date_reception.strftime("%d/%m/%Y à %H:%M")
    
    prompt = f"""Voici un e-mail reçu par le Chef d'Établissement relatant un événement qui doit être consigné dans la Main Courante.

{tags_instruction}
--- DÉBUT DE L'E-MAIL SOUCHE ---
Date de réception : {date_str}
Expéditeur : {mail.expediteur}
Sujet : {mail.sujet}

Contenu brut du message :
{mail.contenu_texte}
--- FIN DE L'E-MAIL SOUCHE ---

Tu dois le transformer en une entrée formelle pour la Main Courante en suivant scrupuleusement les instructions système.
"""
    return prompt

def build_main_courante_text_prompt(raw_text: str, existing_tags: Optional[List[str]] = None) -> str:
    """
    Construit le prompt utilisateur pour générer une entrée de main courante 
    à partir d'un compte-rendu dicté sur Telegram (Pipeline B).
    
    Args:
        raw_text (str): La description brute, textuelle ou vocale transcrite, 
                        fournie par le chef d'établissement.
        existing_tags (Optional[List[str]]): Les tags existants dans le document 
                                             pour harmoniser l'indexation.
        
    Returns:
        str: Le prompt formaté contenant le texte dicté et les consignes de formatage.
    """
    tags_instruction = ""
    if existing_tags:
        tags_list = ", ".join(existing_tags)
        tags_instruction = (
            f"Pour assurer la cohérence de l'indexation du registre, voici la liste des balises (tags) "
            f"déjà utilisées dans le document. RÉUTILISE-LES EN PRIORITÉ s'ils sont pertinents "
            f"pour décrire cet incident : {tags_list}\n"
        )

    # Date et heure au moment de la dictée sur Telegram
    current_time = datetime.now().strftime("%d/%m/%Y à %H:%M")

    prompt = f"""Voici un compte-rendu brut (transcription vocale ou texte rapide) dicté par le Chef d'Établissement via sa messagerie sécurisée. 


{tags_instruction}
--- DÉBUT DU COMPTE-RENDU BRUT ---
Date et heure de la transmission : {current_time}
Texte dicté :
"{raw_text}"
--- FIN DU COMPTE-RENDU BRUT ---
Tu dois le transformer en une entrée formelle pour la Main Courante en suivant scrupuleusement les instructions système.
"""
    return prompt