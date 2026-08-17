import re
from typing import Optional, List
from src.utils import get_logger, truncate_text_for_llm, get_past_school_year_prefixes
from src.core import get_drive_service, get_settings

# Initialisation du logger
logger = get_logger(__name__)

async def preparer_brouillon_main_courante(texte_brut: str) -> str:
    """
    Analyse un compte-rendu informel d'incident et prépare un brouillon formaté, neutre 
    et juridique pour la Main Courante de l'établissement (au format Markdown).
    
    ATTENTION POUR LE COPILOTE : Cet outil NE SAUVEGARDE PAS le texte. Il te renvoie 
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


async def rechercher_info_drive(mots_cles: str, annee_archive: Optional[str] = None) -> str:
    """
    Recherche des mots-clés dans le contenu des documents du Google Drive et renvoie leur contenu.
    Utile pour trouver des procédures, des protocoles, des compte-rendus de réunion, des documents de travail ou des informations administratives.
    Par défaut, la recherche se limite aux documents permanents et à ceux de l'année scolaire en cours.
    
    Args:
        mots_cles (str): Les mots-clés à rechercher (ex: "protocole harcèlement", "budget 2024").
                         Privilégier 2 à 3 mots-clés maximum.
        annee_archive (Optional[str]): Vide par défaut (recherche dans l'année en cours). 
                                       Si l'utilisateur demande explicitement une recherche dans 
                                       une année scolaire passée, tu DOIS déduire l'année de rentrée 
                                       correspondante, isoler ses 2 derniers chiffres, et fournir 
                                       STRICTEMENT ce paramètre sous la forme du préfixe 'RXX_'.
                                       Exemples : 
                                       - Pour "l'an dernier" (si on est par exemple en novembre 2025 ou bien en mai 2026) -> "R24_"
                                       - Pour "les archives de 2023-2024" -> "R23_"
                                       - Pour "en 2021" -> "R21_"
                                       - Pour "les archives de R25" --> "R25_"
                         
    Returns:
        str: Le contenu textuel des documents trouvés avec leur nom et URL d'accès, ou un message si rien n'est trouvé.
    """
    logger.info(f"Outil rechercher_info_drive appelé. Mots-clés: '{mots_cles}' | Archive ciblée : {annee_archive}")
    
    try:
        # Récupération du singleton du service Drive via l'injection de dépendances
        drive_service = get_drive_service()
        
        # --- GESTION TEMPORELLE ET EXCLUSION ---
        prefixes_a_exclure = None
        settings = get_settings()
        
        if not annee_archive:
            # Comportement par défaut : on génère et on exclut toutes les années précédentes
            prefixes_a_exclure = get_past_school_year_prefixes(start_year=settings.ARCHIVE_START_YEAR)
        else:
            # L'IA a formaté l'argument (ex: "R24_"). On l'injecte dans la recherche pour cibler l'archive.
            mots_cles = f"{annee_archive} {mots_cles}"
        # ---------------------------------------
        
        # 1. On cherche les documents limités à 3 pour préserver la fenêtre de contexte
        fichiers_trouves = await drive_service.search_files_by_content(
            query_string=mots_cles, 
            limit=3,
            excluded_prefixes=prefixes_a_exclure
        )
        
        if not fichiers_trouves:
            mention = f" pour l'archive {annee_archive}" if annee_archive else " (parmi les fichiers permanents et de l'année en cours)"
            return f"Aucune information trouvée dans le Drive pour : '{mots_cles}'{mention}."
            
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



async def lire_memoire_etablissement() -> str:
    """
    Lit et retourne le contenu intégral du document officiel "Mémoire de l'Établissement".
    ATTENTION POUR LE COPILOTE : Utilise cet outil SANS AUCUN PARAMÈTRE dès que tu as 
    besoin de connaître les règles de l'établissement, l'annuaire du personnel (qui fait quoi), 
    ou l'historique récent du collège pour comprendre le contexte d'une demande.
    """
    logger.info("Outil 'lire_memoire_etablissement' appelé par l'Orchestrateur.")

    try:
        drive_service = get_drive_service()
        settings = get_settings()
        file_id = settings.MEMOIRE_FILE_ID
        
        # On utilise le téléchargement en texte brut ultra-léger
        contenu = await drive_service.get_file_text_content(
            file_id=file_id, 
            mime_type='application/vnd.google-apps.document'
        )
        
        return f"Voici le contenu de la Mémoire de l'Établissement :\n\n{contenu}"
        
    except Exception as e:
        logger.error(f"Erreur lors de la lecture directe de la mémoire : {e}")
        return "Erreur technique : Impossible d'accéder au fichier Mémoire de l'Établissement."


async def generer_brouillon_synthese_hebdo() -> str:
    """
    Génère un brouillon de synthèse hebdomadaire sous forme de Google Doc, en regroupant 
    tous les échanges récents non synthétisés.
    ATTENTION POUR LE COPILOTE : Utilise cet outil UNIQUEMENT quand le chef d'établissement 
    demande de préparer la synthèse du document "Mémoire de l'établissement".
    Dans ce cas là, aucun autre outil n'est nécessaire (ne recherche pas dans le drive, ni dans les mails ou autre).
    """
    from src.utils import get_logger, truncate_text_for_llm
    logger = get_logger(__name__)
    logger.info("Outil 'generer_brouillon_synthese_hebdo' appelé.")
    
    try:
        from src.core.config import get_settings
        from src.core.dependencies import get_drive_service, get_pipeline_b
        from src.agents.synth_agent import SynthAgent
        from datetime import datetime
        
        settings = get_settings()
        drive_service = get_drive_service()
        pipeline_b = get_pipeline_b()
        synth_agent = SynthAgent()  # Instanciation propre de l'Agent
        
        # 1. Collecte des notes en RAM
        notes = []
        async with pipeline_b._memory_lock:
            for turn in pipeline_b.chat_history.turns:
                if not turn.est_synthetise:
                    role = "Perdir" if turn.role == "user" else "Copilote IA"
                    ts = turn.timestamp.strftime("%d/%m %H:%M")
                    notes.append(f"[{ts}] {role} : {turn.message}")
                    
        if not notes:
            return "Il n'y a aucune nouvelle information ou note à synthétiser depuis la dernière fois."
            
        notes_text = "\n".join(notes)
        
        # 2. Récupération structure du fichier maître
        try:
            memoire_structure = await drive_service.get_file_text_content(settings.MEMOIRE_FILE_ID, 'application/vnd.google-apps.document')
            memoire_structure = truncate_text_for_llm(memoire_structure, max_tokens=1500)
        except Exception:
            memoire_structure = "(Structure non disponible)"
            
        # 3. Appel de l'Agent de Synthèse (Le prompt n'est plus ici !)
        html_content = await synth_agent.generate_hebdo_brouillon(notes_text, memoire_structure)

        # --- Interception du refus de synthèse ---
        if "AUCUNE_MODIFICATION_REQUISE" in html_content:
            logger.info("L'Agent de Synthèse a jugé que les notes ne justifiaient pas de création de document.")
            
            # On acquitte quand même les messages en RAM pour ne pas les re-analyser la prochaine fois
            async with pipeline_b._memory_lock:
                for turn in pipeline_b.chat_history.turns:
                    turn.est_synthetise = True
                pipeline_b._save_history()
                
            return "L'analyse a bien été effectuée, mais les informations notées ont été jugées sans impact stratégique. Le document \"Mémoire de l'Établissement\" n'a pas besoin d'être mis à jour et aucun fichier inutile n'a été créé."
        # --------------------------------------------------
            
        # 4. Création du Google Doc via le service
        doc_title = f"Brouillon de Synthèse - {datetime.now().strftime('%d/%m/%Y')}"
        parent_folder = getattr(settings, 'SYNTHESIS_FOLDER_ID', None)
        
        doc_info = await drive_service.create_google_doc(
            title=doc_title, 
            html_content=html_content,
            parent_id=parent_folder # On envoie le fichier dans le bon dossier
        )
        
        # 5. Acquittement des messages en RAM
        async with pipeline_b._memory_lock:
            for turn in pipeline_b.chat_history.turns:
                turn.est_synthetise = True
            pipeline_b._save_history()
            
        return (
            f"✅ Le brouillon de synthèse a été créé avec succès !\n\n"
            f"<b>Titre :</b> {doc_title}\n"
            f"<b>Lien :</b> {doc_info['link']}\n\n"
            f"Vous pouvez cliquer sur le lien, copier ce qui vous intéresse, et le coller dans votre fichier maître."
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la création du brouillon de synthèse : {e}", exc_info=True)
        return "Erreur technique lors de la création du brouillon de synthèse."