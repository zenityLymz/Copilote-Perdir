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

def split_telegram_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Découpe un texte long (ex: Briefing ou Synthèse nocturne) en une liste de 
    messages plus courts pour respecter la limite stricte de l'API Telegram 
    (4096 caractères). Tente de couper proprement sur les sauts de ligne.

    Args:
        text (str): Le texte intégral à envoyer.
        max_length (int): La limite de caractères par morceau (4000 par sécurité).

    Returns:
        List[str]: Une liste de sous-chaînes prêtes à être envoyées séquentiellement.
    """
    pass

def escape_telegram_markdown(text: str) -> str:
    """
    Échappe les caractères spéciaux requis par le parseur 'MarkdownV2' de l'API Telegram 
    (ex: -, ., !, (, )) pour éviter que l'envoi du message ne crashe.
    Cette fonction préserve le formatage généré par le LLM (gras, italique, listes).

    Args:
        text (str): Le texte Markdown généré par l'IA.

    Returns:
        str: Le texte formaté et sécurisé pour l'envoi via le TelegramBotService.
    """
    pass