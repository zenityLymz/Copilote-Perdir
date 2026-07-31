from typing import Optional
from src.utils import get_logger

# Initialisation du logger
logger = get_logger(__name__)

async def rechercher_dans_les_emails(requete_semantique: str) -> str:
    """
    Interroge la mémoire vectorielle de l'établissement pour retrouver une information 
    précise dans la totalité des e-mails (récents ou anciens, lus ou non lus).
    
    ATTENTION POUR L'ORCHESTRATEUR : Utilise cet outil dès que le chef d'établissement 
    te demande de "retrouver", "chercher" ou te pose une question sur un fait passé 
    ou une information contenue dans sa messagerie (ex: "Quelle est la date de la 
    prochaine réunion de bassin ?", "Retrouve le mail de l'inspecteur sur la réforme").
    Ne réponds jamais de mémoire, utilise toujours cet outil pour vérifier les faits.
    Même lorsque le chef d'établissement ne te pas demande explicitement de rechercher 
    dans ses e-mails, mais que tu manques de contexte pour réaliser une action (trouver la 
    date d'un rendez-vous ou le nom d'un parent pour créer ensuite un événement d'agenda ou une tâche), 
    si tu soupçonnes que tu peux trouver des informations dans les e-mails, utilise cet outil 
    pour récupérer des informations pertinentes.
    En revanche, quand le chef d'établissement te demande de résumer ou faire un point sur ses e-mails, 
    c'est l'outil 'consulter_nouveaux_mails' qu'il faut utiliser, pas celui-ci. En effet, avec 'consulter_nouveaux_mails' 
    tu pourras récupérer l'intégralité des e-mails non lus pour ensuite les résumer, 
    alors que cet outil ne te donnera que des extraits pertinents relatifs à une question précise.

    Args:
        requete_semantique (str): La question exacte de l'utilisateur ou les concepts 
                                  clés à rechercher, formulés en langage naturel clair 
                                  (ex: "date réunion chefs établissement bassin").

    Returns:
        str: Le contexte textuel reconstitué à partir des e-mails les plus pertinents, 
             ou un message clair si rien n'a été trouvé.
    """
    from src.services.chroma_service import ChromaDBService
    from src.core.config import get_settings
    
    logger.info(f"Outil 'rechercher_dans_les_emails' appelé avec la requête : '{requete_semantique}'")
    
    try:
        settings = get_settings()
        # Initialisation du service ChromaDB (qui pointe vers le dossier local)
        chroma_service = ChromaDBService(persist_directory=settings.CHROMA_PERSIST_DIR)
        
        # On demande les 5 e-mails les plus pertinents sémantiquement
        resultats = await chroma_service.search_semantic(query=requete_semantique, n_results=5)
        
        if not resultats:
            return "Aucun e-mail pertinent n'a été trouvé dans la base de données pour cette recherche."
            
        # Formatage des résultats pour que l'Orchestrateur (LLM) puisse les lire facilement
        contexte_formate = "Voici les extraits d'e-mails trouvés dans la base de données :\n\n"
        
        for i, res in enumerate(resultats, 1):
            meta = res.get('metadata', {})
            date_reception = meta.get('date_reception', 'Date inconnue')
            expediteur = meta.get('expediteur', 'Expéditeur inconnu')
            sujet = meta.get('sujet', 'Sans objet')
            texte = res.get('document', '')
            
            contexte_formate += f"--- E-MAIL {i} ---\n"
            contexte_formate += f"Date : {date_reception}\n"
            contexte_formate += f"De : {expediteur}\n"
            contexte_formate += f"Sujet : {sujet}\n"
            contexte_formate += f"Extrait du contenu : {texte}\n"
            contexte_formate += "-" * 20 + "\n\n"
            
        return contexte_formate
        
    except Exception as e:
        logger.error(f"Échec de la recherche vectorielle dans les e-mails : {e}")
        return "Erreur technique : impossible d'accéder à la base de données des e-mails pour le moment."

async def enregistrer_brouillon_mail(destinataire: str, sujet: str, corps_message: str) -> bool:
    """
    Outil agissant comme un "bras robotique" pour injecter un e-mail dans le dossier 
    "Brouillons" (Drafts) de la messagerie académique du chef d'établissement.
    
    ATTENTION POUR L'ORCHESTRATEUR : Tu dois D'ABORD rédiger toi-même la réponse 
    complète avant d'appeler cet outil.

    Args:
        destinataire (str): L'adresse e-mail exacte du ou des destinataire(s).
        sujet (str): L'objet synthétique de l'e-mail.
        corps_message (str): Le contenu complet du message.

    Returns:
        bool: True si le brouillon a été synchronisé sur le serveur avec succès, False sinon.
    """
    from src.services.imap_service import IMAPService
    
    logger.info(f"Outil 'enregistrer_brouillon_mail' appelé pour le ou les destinataire(s) : {destinataire}")
    
    # L'outil instancie son propre accès IMAP de manière éphémère
    imap_service = IMAPService()
    
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

async def generer_briefing_emails(criteres: Optional[str] = None) -> str:
    """
    Se connecte en direct à la messagerie pour relever les e-mails récents ou non lus, 
    et génère un résumé intelligent selon les instructions fournies.
    
    ATTENTION POUR L'ORCHESTRATEUR : Utilise cet outil lorsque le chef d'établissement 
    te demande explicitement un "résumé", un "point sur ses mails", ou cherche à savoir 
    s'il a reçu quelque chose de nouveau concernant un sujet précis (ex: "Ai-je des 
    urgences ce matin ?", "Fais-moi un point des nouveaux mails uniquement sur le financier", "Y a-t-il des messages 
    de la DEC ?").

    Args:
        criteres (Optional[str]): Les instructions de filtrage dictées par l'utilisateur 
                                  en langage naturel (ex: "uniquement les urgences", 
                                  "les mails parlant de budget", "les messages des parents"). 
                                  Si l'utilisateur demande juste un point général, laisse vide.

    Returns:
        str: Le résumé structuré des e-mails correspondants généré par l'Agent de Briefing, 
             ou un message indiquant qu'aucun nouveau mail ne correspond.
    """
    from src.services.imap_service import IMAPService
    from src.agents.briefing_agent import BriefingAgent
    from src.core.config import get_settings
    
    logger.info(f"Outil 'generer_briefing_emails' appelé avec les critères : '{criteres}'")    
    imap_service = IMAPService()
    settings = get_settings()
    
    briefing_agent = BriefingAgent(
        api_key=settings.GEMINI_API_KEY, 
        model_name=settings.GEMINI_FLASH_MODEL
    )
    
    try:
        await imap_service.connect()
        
        # On utilise la nouvelle méthode qui scanne dynamiquement toute l'arborescence
        tous_les_nouveaux_mails = await imap_service.fetch_all_unseen_emails(limit_per_folder=20)
        
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