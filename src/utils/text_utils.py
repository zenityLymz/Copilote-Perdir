import logging
from typing import Optional, List
from bs4 import BeautifulSoup
import re
from email.utils import parseaddr

# Initialisation du logger pour le module
logger = logging.getLogger(__name__)

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
    if not raw_html or not isinstance(raw_html, str):
        return ""

    try:
        # Initialisation de BeautifulSoup avec le parser standard de Python
        soup = BeautifulSoup(raw_html, "html.parser")

        # Destruction des balises invisibles ou polluantes
        for script_or_style in soup(["script", "style", "head", "title", "meta"]):
            script_or_style.decompose()

        # Extraction du texte en utilisant un saut de ligne comme séparateur de blocs
        text = soup.get_text(separator="\n")

        # Nettoyage des espaces superflus et des sauts de ligne multiples
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Reconstitution d'un texte propre et aéré
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)

        return cleaned_text

    except Exception as e:
        logger.error(f"Échec du nettoyage HTML : {e}", exc_info=True)
        # Dégradation gracieuse : on renvoie la chaîne d'origine au lieu de crasher le pipeline
        return raw_html

    
def extract_email_address(header_string: str) -> Optional[str]:
    """
    Extrait l'adresse e-mail pure à partir d'un en-tête d'expéditeur complexe.
    Exemple: "Jean Dupont <jean.dupont@ac-lyon.fr>" -> "jean.dupont@ac-lyon.fr"

    Args:
        header_string (str): La chaîne de l'en-tête (From) contenant le contact.

    Returns:
        Optional[str]: L'adresse e-mail isolée, ou None si le format n'est pas reconnu.
    """
    # 1. Vérification défensive des types et de la validité de l'entrée
    if not header_string or not isinstance(header_string, str):
        return None

    try:
        # 2. Utilisation de la librairie standard (robuste pour la norme RFC 2822)
        # parseaddr renvoie un tuple ('Nom complet', 'adresse@email.com')
        _, email_address = parseaddr(header_string)
        
        if email_address and '@' in email_address:
            return email_address.strip().lower()
        
        # 3. Fallback (Solution de repli) : Regex si l'en-tête est sévèrement malformé
        # Cherche le motif standard d'un e-mail n'importe où dans la chaîne
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', header_string)
        if match:
            return match.group(0).strip().lower()

        # Si on arrive ici, c'est qu'aucune adresse valide n'a pu être extraite
        return None
        
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de l'extraction de l'e-mail depuis '{header_string}' : {e}")
        return None

    
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
    if not text or not isinstance(text, str):
        return 0
        
    try:
        # Heuristique prudente pour la langue française : ~3 caractères = 1 token.
        # On utilise la division entière (//) pour des raisons de performance.
        # On ajoute un "buffer" arbitraire de 5 tokens pour couvrir d'éventuels 
        # marqueurs de début/fin de séquence ajoutés par le modèle en interne.
        estimation = (len(text) // 3) + 5
        
        return estimation
        
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de l'estimation des tokens : {e}")
        # Dégradation gracieuse : on calcule rudimentairement pour éviter de crasher
        return len(str(text)) // 3
    

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
    if not text or not isinstance(text, str):
        return ""
        
    try:
        # Conversion de la limite de tokens en limite de caractères 
        # (Basé sur notre heuristique : 1 token ~ 3 caractères)
        max_chars = max_tokens * 3
        
        # Si le texte est déjà dans les limites, on le retourne intact
        if len(text) <= max_chars:
            return text
            
        # Coupe brute initiale à la limite autorisée
        truncated = text[:max_chars]
        
        # Recherche du meilleur point de coupure naturel en partant de la fin
        # 1er choix : Le dernier saut de ligne (le plus propre)
        cut_index = truncated.rfind('\n')
        
        # 2ème choix : Si pas de saut de ligne, on cherche la fin d'une phrase
        if cut_index == -1:
            cut_index = truncated.rfind('. ')
            
        # 3ème choix : Si pas de point, on cherche au moins un espace pour ne pas couper un mot
        if cut_index == -1:
            cut_index = truncated.rfind(' ')
            
        # Si un point de coupure logique a été trouvé, on réajuste la chaîne
        if cut_index > 0:
            # On inclut le point final s'il s'agit d'une fin de phrase
            if truncated[cut_index] == '.':
                cut_index += 1
            truncated = truncated[:cut_index]
            
        # Ajout d'une balise claire pour informer le LLM (et le Perdir) de la coupure
        return truncated.strip() + "\n\n... [DOCUMENT TRONQUÉ CAR TROP LONG] ..."
        
    except Exception as e:
        logger.warning(f"Erreur inattendue lors de la troncature du texte : {e}")
        # Dégradation gracieuse : coupe de force sans réflexion
        return text[:(max_tokens * 3)] + " [...]"


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