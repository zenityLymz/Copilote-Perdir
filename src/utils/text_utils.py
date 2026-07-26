from typing import Optional

def clean_html_content(raw_html: str) -> str:
    """
    Nettoie le contenu HTML d'un e-mail pour en extraire uniquement le texte brut.
    
    Cette étape est cruciale pour préparer un e-mail avant de générer ses embeddings 
    vectoriels ou de le soumettre à l'agent de triage, afin d'éviter la pollution 
    par des balises inutiles.

    Args:
        raw_html (str): Le corps du message au format HTML brut.

    Returns:
        str: Le texte extrait et nettoyé des balises et scripts.
    """
    pass

def estimate_token_count(text: str) -> int:
    """
    Estime de manière heuristique le nombre de tokens d'une chaîne de caractères.
    
    Permet de renseigner le champ `nombre_tokens` du modèle `MailObject` et de 
    sécuriser l'envoi vers l'API Gemini ou l'API d'embeddings en évitant 
    les erreurs de dépassement de la fenêtre de contexte.

    Args:
        text (str): Le texte dont on souhaite évaluer la taille.

    Returns:
        int: Une estimation du nombre de tokens.
    """
    pass

def truncate_text_for_llm(text: str, max_tokens: int) -> str:
    """
    Tronque intelligemment un texte s'il dépasse une certaine limite de tokens.
    
    L'algorithme tentera de couper proprement (par exemple au dernier point 
    ou saut de ligne) plutôt qu'en plein milieu d'un mot.

    Args:
        text (str): Le texte source à potentiellement raccourcir.
        max_tokens (int): La limite de tolérance haute de tokens.

    Returns:
        str: Le texte tronqué (avec potentiellement un indicateur "[...]") 
             ou le texte original s'il respectait la limite.
    """
    pass

def sanitize_filename(filename: str) -> str:
    """
    Nettoie une chaîne de caractères pour qu'elle soit compatible avec les 
    systèmes de fichiers locaux et Google Drive.
    
    Utile pour l'enregistrement local de pièces jointes ou le nommage
    des documents dans la "Main Courante".

    Args:
        filename (str): Le nom de fichier brut issu de la source.

    Returns:
        str: Un nom de fichier sécurisé, dépourvu de caractères spéciaux ou illégaux.
    """
    pass

def extract_email_address(header_string: str) -> Optional[str]:
    """
    Extrait l'adresse e-mail pure à partir d'un en-tête d'expéditeur complexe.
    
    Exemple: "Jean Dupont <jean.dupont@ac-lyon.fr>" -> "jean.dupont@ac-lyon.fr"

    Args:
        header_string (str): La chaîne de l'en-tête (From, To, Cc) contenant le contact.

    Returns:
        Optional[str]: L'adresse e-mail isolée, ou None si le format n'est pas reconnu.
    """
    pass