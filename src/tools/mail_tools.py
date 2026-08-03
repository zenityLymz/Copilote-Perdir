from typing import Optional
from src.utils import get_logger
from src.core import get_imap_service, get_chroma_service

# Initialisation du logger
logger = get_logger(__name__)

async def rechercher_dans_les_emails(
    requete_semantique: str, 
    date_debut: Optional[str] = None, 
    date_fin: Optional[str] = None,
    expediteur: Optional[str] = None
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

    Returns:
        str: Le contexte textuel reconstitué à partir des e-mails les plus pertinents, 
             ou un message clair si rien n'a été trouvé.
    """
    
    logger.info(
        f"Outil 'rechercher_dans_les_emails' appelé. Requête: '{requete_semantique}' | "
        f"Expéditeur: '{expediteur}' | Période: {date_debut or 'Origine'} -> {date_fin or 'Aujourdhui'}"
    )

    chroma_service = get_chroma_service()
    
    try:
        # 1. Construction dynamique des conditions de filtrage ChromaDB
        conditions = []
        
        if date_debut:
            conditions.append({"date_reception": {"$gte": date_debut}})
        if date_fin:
            conditions.append({"date_reception": {"$lte": date_fin}})
        if expediteur:
            # Utilisation de $contains car l'en-tête "From" est souvent complexe 
            # (ex: "Jean Dupont <jean.dupont@ac-lyon.fr>")
            conditions.append({"expediteur": {"$contains": expediteur}})
            
        # 2. Assemblage final du filter_metadata
        filter_metadata = None
        if len(conditions) > 1:
            # ChromaDB nécessite $and pour de multiples conditions
            filter_metadata = {"$and": conditions}
        elif len(conditions) == 1:
            # S'il n'y a qu'une seule condition, on la passe directement
            filter_metadata = conditions[0]

        # 3. Recherche vectorielle avec sur-échantillonnage (15 résultats au lieu de 5)
        resultats = await chroma_service.search_semantic(
            query=requete_semantique, 
            n_results=15, 
            filter_metadata=filter_metadata
        )
        
        if not resultats:
            return "Aucun e-mail pertinent n'a été trouvé dans la base de données pour cette recherche (avec les filtres spécifiés)."
            
        # 4. Formatage pour l'ingestion par l'Orchestrateur
        contexte_formate = "Voici les extraits d'e-mails trouvés dans la base de données :\n\n"
        
        for i, res in enumerate(resultats, 1):
            meta = res.get('metadata', {})
            date_reception = meta.get('date_reception', 'Date inconnue')
            mail_expediteur = meta.get('expediteur', 'Expéditeur inconnu')
            sujet = meta.get('sujet', 'Sans objet')
            texte = res.get('document', '')
            
            contexte_formate += f"--- E-MAIL {i} ---\n"
            contexte_formate += f"Date : {date_reception}\n"
            contexte_formate += f"De : {mail_expediteur}\n"
            contexte_formate += f"Sujet : {sujet}\n"
            contexte_formate += f"Extrait du contenu : {texte}\n"
            contexte_formate += "-" * 20 + "\n\n"
            
        return contexte_formate
        
    except Exception as e:
        logger.error(f"Échec de la recherche vectorielle dans les e-mails : {e}", exc_info=True)
        return "Erreur technique : impossible d'accéder à la base de données des e-mails pour le moment."

async def enregistrer_brouillon_mail(destinataire: str, sujet: str, corps_message: str) -> bool:
    """
    Outil agissant comme un "bras robotique" pour injecter un e-mail dans le dossier 
    "Brouillons" (Drafts) de la messagerie académique du chef d'établissement.
    
    ATTENTION POUR LE COPILOTE : Tu dois D'ABORD rédiger toi-même la réponse 
    complète avant d'appeler cet outil.

    Args:
        destinataire (str): L'adresse e-mail exacte du ou des destinataire(s).
        sujet (str): L'objet synthétique de l'e-mail.
        corps_message (str): Le contenu complet du message.

    Returns:
        bool: True si le brouillon a été synchronisé sur le serveur avec succès, False sinon.
    """
    
    logger.info(f"Outil 'enregistrer_brouillon_mail' appelé pour le ou les destinataire(s) : {destinataire}")
    
    # Récupération de l'instance IMAP déjà connectée depuis le registre
    imap_service = get_imap_service()
    
    try:
        await imap_service.connect()
        # Le nom du dossier Brouillons dépend souvent du serveur (Drafts ou Brouillons). 
        # "Drafts" est le standard technique IMAP.
        succes = await imap_service.save_draft(destinataire, sujet, corps_message, dossier_brouillons='"Drafts"')
        return succes
    except Exception as e:
        logger.error(f"Échec de l'exécution de l'outil enregistrer_brouillon_mail : {e}")
        return False
    finally:
        await imap_service.disconnect()

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
    
    briefing_agent = BriefingAgent(
        api_key=settings.GEMINI_API_KEY, 
        model_name=settings.GEMINI_FLASH_MODEL
    )
    
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