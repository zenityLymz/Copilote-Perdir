from typing import Optional, List

def clean_html_content(raw_html: str) -> str:
    """
    Nettoie le contenu HTML d'un e-mail pour en extraire uniquement le texte brut.
    Crucial pour préparer un e-mail avant de l'envoyer au TriageAgent (Pipeline A) 
    ou de générer ses embeddings vectoriels.

    Args:
        raw_html (str): Le corps du message au format HTML brut.

    Returns:
        str: Le texte extrait et nettoyé des balises et scripts.
    """
    pass

def extract_email_address(header_string: str) -> Optional[str]:
    """
    Extrait l'adresse e-mail pure à partir d'un en-tête d'expéditeur complexe.
    Exemple: "Jean Dupont <jean.dupont@ac-lyon.fr>" -> "jean.dupont@ac-lyon.fr"

    Args:
        header_string (str): La chaîne de l'en-tête (From) contenant le contact.

    Returns:
        Optional[str]: L'adresse e-mail isolée, ou None si le format n'est pas reconnu.
    """
    pass

def estimate_token_count(text: str) -> int:
    """
    Estime de manière heuristique le nombre de tokens d'une chaîne de caractères.
    Permet de sécuriser l'envoi vers l'API Gemini ou l'API d'embeddings en évitant 
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
    Coupe proprement (au dernier point ou saut de ligne) plutôt qu'en plein milieu d'un mot.

    Args:
        text (str): Le texte source à potentiellement raccourcir.
        max_tokens (int): La limite de tolérance haute de tokens.

    Returns:
        str: Le texte tronqué (avec un indicateur "[...]") ou le texte original.
    """
    pass


def split_telegram_message(text: str, max_length: int = 4096) -> List[str]:
    """
    Découpe un texte trop long en plusieurs morceaux pour respecter 
    la limite de caractères de l'API Telegram.
    
    Tente de couper intelligemment sur les sauts de ligne pour éviter 
    de casser des phrases ou le formatage Markdown (gras, listes).

    Args:
        text (str): Le texte généré par l'IA à envoyer.
        max_length (int): La limite maximale de Telegram (4096).

    Returns:
        List[str]: Une liste contenant les différents morceaux du message.
    """
    if not text:
        return []
        
    chunks = []
    
    while len(text) > max_length:
        # On cherche le dernier saut de ligne présent AVANT la limite des 4096 caractères
        split_index = text.rfind('\n', 0, max_length)
        
        # Si on ne trouve aucun saut de ligne (texte très compact), on coupe de force à la limite
        if split_index == -1:
            split_index = max_length
            
        # On ajoute le morceau à la liste
        chunks.append(text[:split_index])
        
        # On met à jour le texte restant en enlevant les espaces/retours à la ligne résiduels au début
        text = text[split_index:].lstrip()
        
    # S'il reste du texte à la fin de la boucle, on l'ajoute
    if text:
        chunks.append(text)
        
    return chunks