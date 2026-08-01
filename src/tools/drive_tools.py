import logging
from src.services.google_drive_api import GoogleDriveService

logger = logging.getLogger(__name__)

def rechercher_info_drive(mots_cles: str) -> str:
    """
    Recherche des mots-clés dans le contenu des documents du Google Drive et renvoie leur contenu.
    Utile pour trouver des procédures, des protocoles, des compte-rendus de réunion, des documents de travail ou des informations administratives.
    
    Args:
        mots_cles (str): Les mots-clés à rechercher (ex: "protocole harcèlement", "budget 2024").
                         Privilégier 2 à 3 mots-clés maximum.
                         
    Returns:
        str: Le contenu textuel des documents trouvés avec leur nom et emplacement ou un message si rien n'est trouvé.
    """
    logger.info(f"Outil rechercher_info_drive appelé avec les mots-clés : {mots_cles}")
    
    try:
        drive_service = GoogleDriveService()
        
        # 1. On cherche les IDs des fichiers qui contiennent ces mots
        # On limite à 3 pour ne pas saturer la fenêtre de contexte de l'agent
        fichiers_trouves = drive_service.search_files_by_content(mots_cles, limit=3)
        
        if not fichiers_trouves:
            return f"Aucune information trouvée dans le Drive pour : '{mots_cles}'."
            
        resultat_texte = f"Voici les extraits des documents trouvés dans le Drive pour '{mots_cles}' :\n\n"
        
        # 2. On boucle pour récupérer le texte de chaque document
        for fichier in fichiers_trouves:
            file_id = fichier.get('id')
            file_name = fichier.get('name')
            
            try:
                # On demande au service d'extraire le texte brut du fichier
                contenu = drive_service.get_file_text_content(file_id) 
                
                # Sécurité : on tronque si le document est vraiment trop long 
                # (ex: 4000 caractères correspond environ à 1000 tokens)
                limite_chars = 4000
                if len(contenu) > limite_chars:
                    contenu = contenu[:limite_chars] + "\n... [DOCUMENT TRONQUÉ CAR TROP LONG] ..."
                
                resultat_texte += f"--- Source : Document Drive '{file_name}' ---\n"
                resultat_texte += f"{contenu}\n\n"
                
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du fichier {file_name}: {e}")
                resultat_texte += f"--- Source : '{file_name}' (Impossible d'en extraire le texte) ---\n\n"

        return resultat_texte

    except Exception as e:
        logger.error(f"Erreur globale dans rechercher_info_drive: {e}")
        return "Une erreur technique est survenue lors de la recherche dans le Drive."

def ajouter_main_courante(texte_brut: str) -> bool:
    """
    Transforme un compte-rendu oral ou informel en une entrée formelle, neutre et juridique, 
    puis l'ajoute automatiquement au registre officiel (Main_Courante.md) de l'établissement 
    sur Google Drive.
    
    Utiliser cet outil UNIQUEMENT lorsque l'utilisateur signale un incident, un conflit, 
    ou un événement sensible nécessitant d'être tracé officiellement.

    Args:
        texte_brut (str): Le compte-rendu brut, les notes vocales transcrites ou 
                        la description informelle de l'incident dictée par l'utilisateur.

    Returns:
        bool: True si l'entrée a été ajoutée avec succès au fichier Drive, False en cas d'erreur.
    """
    pass