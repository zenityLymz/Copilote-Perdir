import re
from typing import Optional, List
from src.utils import get_logger, truncate_text_for_llm
from src.core import get_drive_service, get_settings

# Initialisation du logger
logger = get_logger(__name__)

async def preparer_brouillon_main_courante(texte_brut: str) -> str:
    """
    Analyse un compte-rendu informel d'incident et prépare un brouillon formaté, neutre 
    et juridique pour la Main Courante de l'établissement (au format Markdown).
    
    ATTENTION POUR L'ORCHESTRATEUR : Cet outil NE SAUVEGARDE PAS le texte. Il te renvoie 
    uniquement un brouillon. Tu DOIS IMPÉRATIVEMENT présenter ce brouillon au chef 
    d'établissement sur Telegram et lui demander explicitement : "Validez-vous cet ajout ?".
    Ce n'est qu'après son accord que tu pourras utiliser l'outil de sauvegarde.

    Args:
        texte_brut (str): Le compte-rendu brut, les notes vocales transcrites ou 
                          la description informelle de l'incident dictée par l'utilisateur.

    Returns:
        str: Le brouillon généré, accompagné des consignes strictes d'affichage HTML pour Telegram.
    """
    logger.info("Outil 'preparer_brouillon_main_courante' appelé.")
    
    drive_service = get_drive_service()
    settings = get_settings()
    file_id = settings.MAIN_COURANTE_FILE_ID
    
    existing_tags = []
    
    # 1. Lecture du fichier actuel pour extraire les tags
    try:
        content = await drive_service.download_file_content(file_id)
        
        # Extraction astucieuse des tags avec des expressions régulières (Regex)
        tags_personnes = set(re.findall(r'@[A-Za-z0-9_]+', content))
        tags_evenements = set(re.findall(r'#[A-Za-z0-9_]+', content))
        
        existing_tags = list(tags_personnes | tags_evenements)
        logger.debug(f"{len(existing_tags)} tags uniques extraits de la main courante existante.")
        
    except Exception as e:
        logger.warning(f"Impossible de lire la main courante pour extraire les anciens tags : {e}")

    # 2. Création du brouillon en Markdown via le sous-agent spécialisé
    try:
        from src.agents import MainCouranteAgent
        agent = MainCouranteAgent()
        
        brouillon = await agent.format_from_text(
            raw_text=texte_brut, 
            existing_tags=existing_tags
        )
        
        logger.info("Brouillon de la main courante généré avec succès.")
        
        # 3. Consignes strictes à l'Orchestrateur (Séparation HTML / Markdown)
        reponse_orchestrateur = (
            "Voici le brouillon généré, destiné au fichier Markdown du Drive.\n\n"
            "RÈGLE D'AFFICHAGE TELEGRAM (HTML STRICT) : Affiche ce brouillon au chef d'établissement "
            "en l'encadrant avec les balises HTML <pre> et </pre> (ou <blockquote>) "
            "pour qu'il s'affiche proprement comme un bloc de citation sur Telegram, et demande sa validation.\n\n"
            "RÈGLE DE SAUVEGARDE : S'il valide l'ajout, tu devras transmettre à l'outil de sauvegarde "
            "le texte exact ci-dessous, SANS tes balises HTML ajoutées.\n\n"
            "---\n"
            f"{brouillon}\n"
            "---"
        )
        return reponse_orchestrateur
        
    except Exception as e:
        logger.error(f"Échec de la génération du brouillon : {e}", exc_info=True)
        return "Erreur technique : impossible de générer le brouillon de la main courante pour le moment."


async def sauvegarder_main_courante_validee(texte_valide: str) -> bool:
    """
    Injecte un enregistrement validé à la fin du fichier Main_Courante.md sur le Google Drive.
    
    ATTENTION POUR LE COPILOTE : Utilise cet outil UNIQUEMENT APRÈS avoir obtenu 
    l'accord explicite du chef d'établissement sur un brouillon que tu lui as présenté.
    Ne modifie pas le texte validé avant de l'envoyer à cet outil.

    Args:
        texte_valide (str): Le texte de l'entrée formatée en Markdown, tel que validé par l'utilisateur.

    Returns:
        bool: True si la sauvegarde a réussi, False sinon.
    """
    logger.info("Outil 'sauvegarder_main_courante_validee' appelé.")
    
    drive_service = get_drive_service()
    settings = get_settings()
    file_id = settings.MAIN_COURANTE_FILE_ID
    
    try:        
        # 1. Récupération du contenu existant
        try:
            contenu_actuel = await drive_service.download_file_content(file_id)
        except Exception as e:
            # Si le fichier vient d'être créé et est totalement vide, l'API peut renvoyer une erreur.
            # On la rattrape gracieusement et on initialise une chaîne vide.
            logger.warning(f"Le fichier existant n'a pas pu être lu (il est peut-être vide) : {e}")
            contenu_actuel = ""
            
        # 2. Concaténation proprement formatée
        # On s'assure qu'il y a un double saut de ligne (\n\n) entre l'ancienne fin de fichier et la nouvelle entrée.
        if contenu_actuel:
            if not contenu_actuel.endswith("\n\n"):
                if contenu_actuel.endswith("\n"):
                    nouveau_contenu = contenu_actuel + "\n" + texte_valide
                else:
                    nouveau_contenu = contenu_actuel + "\n\n" + texte_valide
            else:
                nouveau_contenu = contenu_actuel + texte_valide
        else:
            # Si le fichier était vide, on insère juste le texte
            nouveau_contenu = texte_valide
            
        # 3. Écrasement du fichier sur Drive avec le nouveau contenu intégral (Replace)
        succes = await drive_service.update_file_content(file_id, nouveau_contenu)
        
        if succes:
            logger.info("Nouvelle entrée sauvegardée avec succès à la fin de la Main Courante.")
            
        return succes
        
    except Exception as e:
        logger.error(f"Erreur critique lors de la sauvegarde de la main courante sur le Drive : {e}", exc_info=True)
        return False


async def rechercher_info_drive(mots_cles: str) -> str:
    """
    Recherche des mots-clés dans le contenu des documents du Google Drive et renvoie leur contenu.
    Utile pour trouver des procédures, des protocoles, des compte-rendus de réunion, des documents de travail ou des informations administratives.
    
    Args:
        mots_cles (str): Les mots-clés à rechercher (ex: "protocole harcèlement", "budget 2024").
                         Privilégier 2 à 3 mots-clés maximum.
                         
    Returns:
        str: Le contenu textuel des documents trouvés avec leur nom et URL d'accès, ou un message si rien n'est trouvé.
    """
    logger.info(f"Outil rechercher_info_drive appelé avec les mots-clés : {mots_cles}")
    
    try:
        # Récupération du singleton du service Drive via l'injection de dépendances
        drive_service = get_drive_service()
        
        # 1. On cherche les documents limités à 3 pour préserver la fenêtre de contexte
        fichiers_trouves = await drive_service.search_files_by_content(mots_cles, limit=3)
        
        if not fichiers_trouves:
            return f"Aucune information trouvée dans le Drive pour : '{mots_cles}'."
            
        resultat_texte = f"Voici les extraits des documents trouvés dans le Drive pour '{mots_cles}' :\n\n"
        
        # 2. On itère pour récupérer le texte de chaque document
        for fichier in fichiers_trouves:
            file_id = fichier.get('id')
            file_name = fichier.get('name')
            file_mime = fichier.get('mimeType')
            file_url = fichier.get('webViewLink', 'Lien non disponible')
            
            resultat_texte += f"--- Source : Document Drive '{file_name}' ---\n"
            resultat_texte += f"Lien d'accès pour le chef d'établissement : {file_url}\n"
            
            try:
                # Extraction du contenu textuel asynchrone
                contenu = await drive_service.get_file_text_content(file_id, file_mime) 
                
                # On utilise notre fonction utilitaire intelligente au lieu de la coupe brute.
                contenu_propre = truncate_text_for_llm(contenu, max_tokens=1000)
                
                resultat_texte += f"Contenu extrait :\n{contenu_propre}\n\n"
                
            except ValueError:
                resultat_texte += "(Impossible de lire ce format de fichier. Seuls les GDocs et Textes simples sont lus.)\n\n"
            except Exception as e:
                logger.error(f"Erreur lors de la lecture du fichier {file_name}: {e}")
                resultat_texte += "(Erreur technique lors de la lecture du fichier)\n\n"

        return resultat_texte

    except Exception as e:
        logger.error(f"Erreur globale dans rechercher_info_drive: {e}")
        return "Une erreur technique est survenue lors de la recherche dans le Drive. Vérifiez l'authentification."
