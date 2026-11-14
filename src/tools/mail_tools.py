import os
from typing import Optional
from datetime import datetime
from src.utils import get_logger, truncate_text_for_llm
from src.core import get_imap_service, get_chroma_service
from src.services.chroma_service import ChromaDBService

# Initialisation du logger
logger = get_logger(__name__)

async def rechercher_dans_les_emails(
    requete_semantique: str, 
    date_debut: Optional[str] = None, 
    date_fin: Optional[str] = None,
    expediteur: Optional[str] = None,
    annee_archive: Optional[str] = None
) -> str:
    """
    Interroge la mémoire vectorielle de l'établissement pour retrouver une information 
    précise dans la totalité des e-mails (récents ou anciens, lus ou non lus).

    ATTENTION POUR LE COPILOTE : Utilise cet outil dès que le chef d'établissement 
    te demande de "retrouver", "chercher" ou te pose une question sur un fait passé 
    ou une information contenue dans sa messagerie (ex: "Quelle est la date de la 
    prochaine réunion de bassin ?", "Retrouve le mail de l'inspecteur sur la réforme").
    Ne réponds jamais de mémoire, utilise toujours cet outil pour vérifier les faits.

    Même lorsque le chef d'établissement ne te pas demande explicitement de rechercher 
    dans ses e-mails, mais que tu manques de contexte pour réaliser une action, 
    utilise cet outil pour récupérer des informations pertinentes.

    En revanche, quand le chef d'établissement te demande de résumer ou faire un point sur ses e-mails, 
    c'est l'outil 'generer_briefing_emails' qu'il faut utiliser, pas celui-ci.

    Args:
        requete_semantique (str): La question exacte de l'utilisateur ou les concepts clés enrichis.
        date_debut (Optional[str]): Date de début de la fenêtre de recherche (format ISO 8601).
        date_fin (Optional[str]): Date de fin de la fenêtre de recherche (format ISO 8601).
        expediteur (Optional[str]): Le nom ou l'adresse e-mail (partielle ou complète) de l'expéditeur.
        annee_archive (Optional[str]): Vide par défaut (recherche dans l'année en cours). Si l'utilisateur demande explicitement une recherche dans une année scolaire antérieure, doit être au format YYYY-YYYY (ex: "2024-2025").
    Returns:
        str: Le contexte textuel reconstitué à partir des e-mails les plus pertinents, 
             ou un message clair si rien n'a été trouvé.
    """
    
    logger.info(
        f"Outil 'rechercher_dans_les_emails' appelé. Requête: '{requete_semantique}' | "
        f"Expéditeur: '{expediteur}' | Période: {date_debut or 'Origine'} -> {date_fin or 'Aujourdhui'} | Année archive: {annee_archive or 'Base courante'}"
    )

    # 1. Sélection dynamique de la base de données vectorielle
    if annee_archive:
        # On définit le chemin vers l'archive demandée
        chemin_archive = f"data/chroma_db_{annee_archive}"
        
        # On vérifie d'abord si le dossier existe physiquement
        if not os.path.exists(chemin_archive):
            logger.warning(f"Tentative d'accès à une archive inexistante : {chemin_archive}")
            return f"Erreur : L'archive demandée pour l'année '{annee_archive}' n'existe pas dans le système."
        
        try:
            logger.debug(f"Connexion à la volée à l'archive vectorielle : {chemin_archive}")
            # Instanciation dynamique. (ChromaDB gère son propre cache interne pour ne pas recharger bêtement)
            chroma_service = ChromaDBService(persist_directory=chemin_archive)
        except Exception as e:
            logger.error(f"Impossible de monter l'archive {chemin_archive} en mémoire : {e}", exc_info=True)
            return f"Erreur technique lors du chargement de l'archive '{annee_archive}'."
    else:
        # Cas classique : on récupère l'instance Singleton de l'année en cours
        chroma_service = get_chroma_service()
    
    try:
        # 2. Construction dynamique des conditions de filtrage ChromaDB
        conditions = []
        
        if date_debut:
            # On traduit la chaîne ISO de l'IA en Timestamp Unix mathématique
            ts_debut = int(datetime.fromisoformat(date_debut.replace("Z", "+00:00")).timestamp())
            conditions.append({"date_reception": {"$gte": ts_debut}})
            
        if date_fin:
            ts_fin = int(datetime.fromisoformat(date_fin.replace("Z", "+00:00")).timestamp())
            conditions.append({"date_reception": {"$lte": ts_fin}})

        if expediteur:
            # Utilisation de $contains car l'en-tête "From" est souvent complexe 
            # (ex: "Jean Dupont <jean.dupont@ac-lyon.fr>")
            conditions.append({"expediteur": {"$contains": expediteur}})
            
        # 3. Assemblage final du filter_metadata
        filter_metadata = None
        if len(conditions) > 1:
            # ChromaDB nécessite $and pour de multiples conditions
            filter_metadata = {"$and": conditions}
        elif len(conditions) == 1:
            # S'il n'y a qu'une seule condition, on la passe directement
            filter_metadata = conditions[0]

        # 4. Recherche vectorielle avec sur-échantillonnage (15 résultats au lieu de 5)
        resultats = await chroma_service.search_semantic(
            query=requete_semantique, 
            n_results=15, 
            filter_metadata=filter_metadata
        )
        
        if not resultats:
            mention_archive = f" dans l'archive {annee_archive}" if annee_archive else " dans la base courante"
            return f"Aucun e-mail pertinent n'a été trouvé{mention_archive} pour cette recherche (avec les filtres spécifiés)."
            
        # 5. Formatage pour l'ingestion par l'Orchestrateur
        contexte_formate = "Voici les extraits d'e-mails trouvés dans la base de données :\n\n"
        
        for i, res in enumerate(resultats, 1):
            mail_id = res.get('id', 'ID inconnu')
            meta = res.get('metadata', {})
            date_reception = meta.get('date_reception', 'Date inconnue')
            mail_expediteur = meta.get('expediteur', 'Expéditeur inconnu')
            sujet = meta.get('sujet', 'Sans objet')
            pieces_jointes = meta.get('pieces_jointes', '')
            texte_brut = res.get('document', '')
            
            # --- Troncature intelligente pour alléger le prompt de l'Orchestrateur ---
            # On limite chaque résultat à ~400 tokens (soit environ 1200 caractères)
            texte_tronque = truncate_text_for_llm(texte_brut, max_tokens=400)
            # Formatage sécurisé s'il n'y a pas de pièce jointe
            pj_texte = pieces_jointes if pieces_jointes else "Aucune"
            
            contexte_formate += f"--- E-MAIL {i} ---\n"
            contexte_formate += f"ID_MAIL : {mail_id}\n"
            contexte_formate += f"Date : {date_reception}\n"
            contexte_formate += f"De : {mail_expediteur}\n"
            contexte_formate += f"Sujet : {sujet}\n"
            contexte_formate += f"Pièces jointes : {pj_texte}\n"
            contexte_formate += f"Extrait du contenu : {texte_tronque}\n"
            contexte_formate += "-" * 20 + "\n\n"
            
        return contexte_formate
        
    except Exception as e:
        logger.error(f"Échec de la recherche vectorielle dans les e-mails : {e}", exc_info=True)
        return "Erreur technique : impossible d'accéder à la base de données des e-mails pour le moment."

async def enregistrer_brouillon_mail(destinataire: str, sujet: str, contexte_original: str, directives_de_redaction: str) -> str:
    """
    Outil pour préparer et injecter un e-mail dans le dossier "Brouillons" de la messagerie.
    
    ATTENTION POUR LE COPILOTE : Tu ne dois pas rédiger toi-même la réponse complète.
    Fournis les éléments factuels (le contexte) et tes directives, un agent spécialisé 
    se chargera de la rédaction finale dans le style de l'utilisateur.
    Tu dois d'abord t'assurer d'avoir bien compris le contexte (qui est le destinataire (est-ce un prof, un aed, un parent, un inspecteur, etc.), quel est le sujet, quel est le contexte de l'échange, etc.) avant de transmettre la requête à l'agent spécialisé.
    Dis-toi bien que l'agent spécialisé n'a pas connaissance du contexte de l'établissement donc il faut que tu lui donnes tout ce qui est nécessaire à sa tâche.
    Affiche ENSUITE fidèlement le contenu exact qui t'est retourné par cet outil (pas de texte supplémentaire, et pas de signature par exemple, car celle-ci sera ajoutée automatiquement plus tard lors de l'envoi manuel). Ne modifie jamais le texte généré par l'agent spécialisé, même si tu penses qu'il pourrait être amélioré.
    La seule chose que tu dois faire, c'est de juger si le texte fourni te semble conforme à ce que j'attends. Pour ce faire, à la fin de la réponse que tu m'envoies sur Telegram, après la citation exacte du mail généré, tu dois ajouter : "Validation copilote : ✅ Conforme" ou alors "Validation copilote : 🚨 Non conforme (il manque une information concernant [...] ou bien le style n'est pas respecté, etc.)".

    Args:
        destinataire (str): L'adresse e-mail exacte du ou des destinataire(s).
        sujet (str): L'objet synthétique de l'e-mail.
        contexte_original (str): Le résumé ou texte brut du mail auquel on répond (laisse vide si c'est un nouveau mail spontané).
        directives_de_redaction (str): Tes consignes (ex: "Refuser poliment car la jauge de la salle est atteinte").

    Returns:
        str: Le message de succès contenant le texte exact généré, ou un message d'erreur.
    """
    
    logger.info(f"Outil 'enregistrer_brouillon_mail' appelé pour : {destinataire}")
    logger.info(f"-> Contexte transmis : {contexte_original}")
    logger.info(f"-> Directives de rédaction : {directives_de_redaction}")
    imap_service = get_imap_service()
    
    try:
        # 1. On fait appel au nouvel agent spécialisé pour rédiger le texte
        from src.agents.draft_agent import DraftAgent
        draft_agent = DraftAgent()
        
        corps_message = await draft_agent.generate_draft(
            destinataire=destinataire,
            sujet=sujet,
            contexte_original=contexte_original,
            directives_de_redaction=directives_de_redaction
        )
        
        # 2. Sauvegarde du brouillon sur le serveur IMAP
        succes = await imap_service.save_draft(destinataire, sujet, corps_message, dossier_brouillons='"Drafts"')
        
        if succes:
            # On renvoie le texte exact à l'Orchestrateur pour qu'il le restitue fidèlement
            return f"Le brouillon a été enregistré avec succès. Voici le texte exact qui a été généré :\n\n{corps_message}"
        else:
            return "Erreur technique : impossible d'enregistrer le brouillon sur le serveur."
        
    except Exception as e:
        logger.error(f"Échec de l'exécution de l'outil enregistrer_brouillon_mail : {e}")
        return f"Erreur de l'agent de rédaction : {e}"

async def generer_briefing_emails(criteres: Optional[str] = None, limite: int = 50) -> str:
    """
    Se connecte en direct à la messagerie pour relever les e-mails récents ou non lus, 
    et génère un résumé intelligent selon les instructions fournies.
    
    ATTENTION POUR LE COPILOTE : Utilise cet outil lorsque le chef d'établissement 
    te demande explicitement un "résumé", un "point sur ses mails", ou cherche à savoir 
    s'il a reçu quelque chose de nouveau concernant un sujet précis (ex: "Ai-je des 
    urgences ce matin ?", "Fais-moi un point des nouveaux mails uniquement sur le financier", "Y a-t-il des messages 
    de la DEC ?").

    Args:
        criteres (Optional[str]): Les instructions de filtrage dictées par l'utilisateur 
                                  en langage naturel (ex: "uniquement les urgences", 
                                  "les mails parlant de budget", "les messages des parents").
                                  Si l'utilisateur demande juste un point général, laisse vide.
        limite (int): Le nombre maximum d'e-mails non lus à récupérer par dossier. Défaut à 50.

    Returns:
        str: Le résumé structuré des e-mails correspondants généré par l'Agent de Briefing, 
             ou un message indiquant qu'aucun nouveau mail ne correspond.
    """
    from src.agents.briefing_agent import BriefingAgent
    from src.core.config import get_settings
    
    logger.info(f"Outil 'generer_briefing_emails' appelé avec les critères : '{criteres}' et limite: {limite}")    
    imap_service = get_imap_service()
    settings = get_settings()
    
    briefing_agent = BriefingAgent()
    
    try:
        await imap_service.connect()
        
        # On utilise la nouvelle méthode qui scanne dynamiquement toute l'arborescence
        # en appliquant la limite demandée par l'Orchestrateur
        tous_les_nouveaux_mails = await imap_service.fetch_all_unseen_emails(limit_per_folder=limite)
        
        if not tous_les_nouveaux_mails:
            return "La relève est terminée : vous n'avez aucun e-mail non lu dans l'ensemble de votre messagerie."
            
        logger.debug(f"{len(tous_les_nouveaux_mails)} e-mails non lus transmis à l'Agent de Briefing.")
        
        # Le BriefingAgent lit les mails, applique les critères, et génère le texte final.
        resume = await briefing_agent.generate_briefing(
            emails=tous_les_nouveaux_mails, 
            user_instruction=criteres
        )
        
        return resume
        
    except Exception as e:
        logger.error(f"Échec de la génération du briefing des e-mails : {e}", exc_info=True)
        return "Erreur technique : la relève de la totalité des dossiers a échoué. Le serveur IMAP est peut-être injoignable."
    finally:
        await imap_service.disconnect()


async def transferer_pj_vers_drive(
    sujet_mail: str, 
    expediteur_mail: str, 
    nom_piece_jointe: str, 
    id_dossier_drive: str,
    nouveau_nom: Optional[str] = None,
    ajouter_prefixe_annee: bool = False
) -> str:
    """
    Télécharge une PJ, la renomme éventuellement, et la sauvegarde dans le Drive.
    """
    import os
    import shutil
    from datetime import datetime
    from src.core.dependencies import get_drive_service
    
    logger.info(f"Outil 'transferer_pj_vers_drive' appelé pour '{nom_piece_jointe}'. Nouveau nom: {nouveau_nom}, Préfixe: {ajouter_prefixe_annee}")
    
    imap_service = get_imap_service()
    drive_service = get_drive_service()
    
    try:
        # 1. Téléchargement local depuis le serveur académique
        chemin_fichier_local = await imap_service.download_attachment(
            sujet=sujet_mail, 
            expediteur=expediteur_mail, 
            attachment_name=nom_piece_jointe
        )
        
        if not chemin_fichier_local:
            return f"Erreur : Impossible de télécharger la pièce jointe '{nom_piece_jointe}'."
        
        # 2. Logique de renommage intelligent
        dossier_parent = os.path.dirname(chemin_fichier_local)
        nom_actuel = os.path.basename(chemin_fichier_local)
        nom_base, ext = os.path.splitext(nom_actuel)
        
        # Application du nouveau nom s'il est fourni par l'IA
        nom_final_base = nouveau_nom if nouveau_nom else nom_base
        
        # Calcul mathématique et rigoureux du préfixe RXX_
        if ajouter_prefixe_annee:
            now = datetime.now()
            annee = now.year
            # Si nous sommes avant août (ex: mai 2027), l'année scolaire de rentrée était 2026.
            if now.month < 8:
                annee -= 1
            prefixe = f"R{str(annee)[-2:]}_"
            nom_final_base = f"{prefixe}{nom_final_base}"
            
        nouveau_chemin_local = os.path.join(dossier_parent, f"{nom_final_base}{ext}")
        
        # Renommage physique sur le disque du Raspberry Pi (Google Drive prendra ce nouveau nom)
        os.rename(chemin_fichier_local, nouveau_chemin_local)
        
        # 3. Upload depuis le SSD vers Google Drive
        id_fichier_drive = await drive_service.upload_physical_file(
            file_path=nouveau_chemin_local, 
            parent_id=id_dossier_drive
        )
        
        # 4. Nettoyage du Raspberry Pi
        try:
            if os.path.exists(dossier_parent):
                shutil.rmtree(dossier_parent)
        except Exception as e:
            logger.warning(f"Impossible de supprimer le dossier temporaire {dossier_parent} : {e}")
        
        if id_fichier_drive:
            return f"Succès : Pièce jointe enregistrée sur le Drive sous le nom '{nom_final_base}{ext}'."
        else:
            return "Erreur technique : Le transfert vers Google Drive a échoué."
            
    except Exception as e:
        logger.error(f"Erreur dans l'outil transferer_pj_vers_drive : {e}")
        return "Erreur technique lors du transfert de la pièce jointe."