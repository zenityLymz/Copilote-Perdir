import asyncio
import imaplib
import email
from email import policy
import email.utils
from datetime import datetime
from typing import List, Optional

from src.core.models import MailObject, TriDecision
from src.core.exceptions import IMAPError
from src.core.config import get_settings
from src.utils import get_logger, extract_email_address, clean_html_content, estimate_token_count, truncate_text_for_llm, extract_text_from_attachment

from email.message import EmailMessage
import time


# Initialisation du logger pour ce module
logger = get_logger(__name__)

class IMAPService:
    """
    Gère la connexion et les opérations sur la boîte de messagerie académique via le protocole IMAP.
    Utilise asyncio.to_thread pour ne pas bloquer l'Event Loop principale.
    """

    def __init__(self, host: str = None, user: str = None, password: str = None, port: int = None) -> None:
        """
        Initialise les paramètres de connexion au serveur IMAP.
        Récupère automatiquement les valeurs via config.py si elles ne sont pas passées en paramètre.
        """
        settings = get_settings()
        self.host = host or settings.IMAP_HOST
        self.user = user or settings.IMAP_USER
        self.password = password or settings.IMAP_PASSWORD
        self.port = port or settings.IMAP_PORT
        
        self.mail: Optional[imaplib.IMAP4_SSL] = None
        self._lock = asyncio.Lock()

        logger.debug("Service IMAP initialisé avec la configuration centrale.")


    async def connect(self) -> None:
        """Point d'entrée asynchrone pour la connexion IMAP."""
        async with self._lock:
            await asyncio.to_thread(self._connect_sync)

    def _connect_sync(self) -> None:
        """Logique synchrone de connexion exécutée dans un thread séparé."""
        logger.info(f"Tentative de connexion au serveur IMAP {self.host}:{self.port}...")
        try:
            self.mail = imaplib.IMAP4_SSL(self.host, self.port)
            self.mail.login(self.user, self.password)
            logger.info("Connexion IMAP établie avec succès.")
        except imaplib.IMAP4.error as e:
            logger.error(f"Échec de l'authentification IMAP : {e}")
            raise IMAPError(f"Échec de l'authentification IMAP : {e}")
        except Exception as e:
            logger.error(f"Erreur de réseau ou de connexion au serveur IMAP : {e}")
            raise IMAPError(f"Erreur de connexion au serveur IMAP - {e}")

    async def disconnect(self) -> None:
        """Point d'entrée asynchrone pour la déconnexion."""
        async with self._lock:
            await asyncio.to_thread(self._disconnect_sync)

    def _disconnect_sync(self) -> None:
        """Ferme proprement la connexion IMAP."""
        if self.mail:
            try:
                self.mail.logout()
                logger.info("Déconnexion IMAP réussie.")
            except Exception as e:
                logger.warning(f"Erreur mineure lors de la déconnexion IMAP : {e}")
            finally:
                self.mail = None

    def _ensure_connected(self) -> None:
        """
        Vérifie si la connexion IMAP est toujours active. 
        En cas de perte (Timeout, Pare-feu, Sophos), force une reconnexion transparente.
        """
        try:
            if self.mail:
                # La commande NOOP (No Operation) est le standard pour tester un "ping" IMAP
                status, _ = self.mail.noop()
                if status != 'OK':
                    raise IMAPError("La commande NOOP a échoué, socket probablement corrompu.")
            else:
                self._connect_sync()
                
        except Exception as e:
            logger.warning(f"Connexion IMAP perdue ou instable ({e}). Tentative de reconnexion automatique...")
            # On force le nettoyage de l'ancien socket mort
            try:
                self._disconnect_sync()
            except Exception:
                self.mail = None
                
            # On relance une connexion fraîche
            self._connect_sync()


    async def fetch_unread_emails(self, folder: str = "INBOX", limit: int = 50) -> List[MailObject]:
        """Point d'entrée asynchrone pour relever les e-mails non lus."""
        async with self._lock:
            return await asyncio.to_thread(self._fetch_unread_emails_sync, folder, limit)

    def _fetch_unread_emails_sync(self, folder: str, limit: int) -> List[MailObject]:
        """Logique métier d'extraction et de parsing des mails."""
        self._ensure_connected()

        logger.info(f"Recherche de nouveaux messages non traités dans le dossier '{folder}'...")
        try:
            status, _ = self.mail.select(f'"{folder}"')
            if status != 'OK':
                raise IMAPError(f"Dossier introuvable ou inaccessible : {folder}")

            # Recherche tous les mails qui n'ont PAS le flag personnalisé 'CopiloteTraite'
            # (Qu'ils soient lus ou non lus par l'humain !)
            status, messages = self.mail.uid('search', None, 'UNKEYWORD', 'CopiloteTraite')
            if status != 'OK' or not messages[0]:
                logger.info("Aucun nouveau message trouvé.")
                return []

            mail_ids = messages[0].split()
            mail_ids = mail_ids[-limit:]
            emails_list = []
            
            for mail_id in mail_ids: # On utilise BODY.PEEK[] pour télécharger le mail sans enlever le flag UNSEEN
                status, msg_data = self.mail.uid('fetch', mail_id, '(BODY.PEEK[])')
                if status != 'OK':
                    continue

                mail_obj = self._parse_email_from_bytes(mail_id, msg_data)
                if mail_obj:
                    emails_list.append(mail_obj)

            logger.info(f"{len(emails_list)} e-mail(s) non lu(s) récupéré(s) et formaté(s).")
            return emails_list

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des e-mails : {e}")
            raise IMAPError(f"Erreur lors de la récupération des e-mails : {e}")
    

    async def move_email(self, decision: TriDecision) -> bool:
        """Déplace un e-mail de manière asynchrone."""
        async with self._lock:
            return await asyncio.to_thread(self._move_email_sync, decision)

    def _move_email_sync(self, decision: TriDecision) -> bool:
        """Exécute les commandes IMAP COPY et STORE pour déplacer l'e-mail."""
        self._ensure_connected()
            
        try:
            uid_mail = decision.id_mail.encode('utf-8')
            target_folder = f'"{decision.dossier_cible.value}"'
            
            logger.debug(f"Déplacement de l'e-mail {decision.id_mail} vers le dossier {target_folder}...")
            
            status_copy, _ = self.mail.uid('COPY', uid_mail, target_folder)
            if status_copy != 'OK':
                logger.warning(f"Échec de la copie de l'e-mail {decision.id_mail}.")
                return False
                
            status_store, _ = self.mail.uid('STORE', uid_mail, '+FLAGS', '(\\Deleted)')
            if status_store != 'OK':
                logger.warning(f"Échec du marquage pour suppression de l'e-mail {decision.id_mail}.")
                return False
                
            self.mail.expunge()
            logger.info(f"E-mail {decision.id_mail} déplacé avec succès vers {target_folder}.")
            return True
            
        except Exception as e:
            logger.error(f"Exception lors du déplacement de l'e-mail {decision.id_mail} : {e}")
            return False

    async def mark_as_processed(self, mail_id: str) -> bool:
        """Ajoute un tag invisible IMAP pour indiquer que l'IA a traité cet e-mail."""
        async with self._lock:
            return await asyncio.to_thread(self._mark_as_processed_sync, mail_id)

    def _mark_as_processed_sync(self, mail_id: str) -> bool:
        """Logique IMAP d'ajout de mot-clé (Keyword) personnalisé."""
        self._ensure_connected()
        
            
        try:
            uid_mail = mail_id.encode('utf-8')
            # Ajout du tag personnalisé 'CopiloteTraite' (sans antislash car ce n'est pas un flag système)
            status, _ = self.mail.uid('STORE', uid_mail, '+FLAGS', 'CopiloteTraite')
            success = (status == 'OK')
            if success:
                logger.debug(f"E-mail {mail_id} tagué comme 'CopiloteTraite'.")
            return success
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du tag à l'e-mail {mail_id} : {e}")
            return False


    async def save_draft(self, destinataire: str, sujet: str, contenu_texte: str, dossier_brouillons: str = '"Drafts"') -> bool:
        """
        Point d'entrée asynchrone pour sauvegarder un message dans le dossier des brouillons.
        """
        async with self._lock:
            return await asyncio.to_thread(self._save_draft_sync, destinataire, sujet, contenu_texte, dossier_brouillons)

    def _save_draft_sync(self, destinataire: str, sujet: str, contenu_texte: str, dossier_brouillons: str) -> bool:
        """
        Logique synchrone IMAP (commande APPEND) pour injecter un brouillon.
        """

        self._ensure_connected()
            
        try:
            logger.debug(f"Construction de l'objet e-mail pour {destinataire}...")
            
            # Utilisation de l'API moderne d'email de Python
            msg = EmailMessage()
            msg['Subject'] = sujet
            msg['From'] = self.user
            msg['To'] = destinataire
            msg.set_content(contenu_texte)

            # Génération de la date interne au format IMAP
            date_imap = imaplib.Time2Internaldate(time.time())

            # La commande APPEND pousse le message sur le serveur avec le drapeau \Draft
            status, _ = self.mail.append(
                dossier_brouillons,
                '(\\Draft)',
                date_imap,
                msg.as_bytes()
            )

            if status == 'OK':
                logger.info("Le brouillon a été poussé avec succès sur le serveur IMAP.")
                return True
            else:
                logger.warning(f"Le serveur IMAP a refusé l'enregistrement du brouillon (Status: {status}).")
                return False
                
        except Exception as e:
            logger.error(f"Erreur technique lors de la création du brouillon IMAP : {e}")
            return False


    async def fetch_all_unseen_emails(self, limit_per_folder: int = 20) -> List[MailObject]:
        """
        Point d'entrée asynchrone pour parcourir tous les dossiers IMAP et récupérer
        les e-mails strictement non lus par l'humain (flag UNSEEN).
        """
        async with self._lock:
            return await asyncio.to_thread(self._fetch_all_unseen_emails_sync, limit_per_folder)

    def _fetch_all_unseen_emails_sync(self, limit_per_folder: int) -> List[MailObject]:
        """
        Logique synchrone qui liste tous les dossiers, les sélectionne un par un,
        et récupère les messages UNSEEN.
        """
        import re
        import email
        from email import policy
        import email.utils
        from datetime import datetime
        
        self._ensure_connected()

        logger.info("Récupération de la liste de tous les dossiers IMAP...")
        emails_list = []
        
        try:
            status, folders = self.mail.list()
            if status != 'OK':
                raise IMAPError("Impossible de lister les dossiers de la messagerie.")

            for folder_data in folders:
                folder_str = folder_data.decode('utf-8')
                
                # Extraction propre du nom du dossier (qui se trouve à la fin de la chaîne)
                match = re.search(r'\"([^\"]+)\"$', folder_str)
                if match:
                    folder_name = f'"{match.group(1)}"'
                else:
                    folder_name = folder_str.split()[-1]

                # On sélectionne le dossier en mode lecture seule
                status, _ = self.mail.select(folder_name, readonly=True)
                if status != 'OK':
                    continue # On ignore les dossiers inaccessibles (ex: \Noselect)

                # Recherche STRICTE des mails non lus par l'humain
                status, messages = self.mail.uid('search', None, 'UNSEEN')
                if status != 'OK' or not messages[0]:
                    continue

                mail_ids = messages[0].split()
                # On limite le nombre pour ne pas saturer la mémoire si un dossier a 500 mails non lus
                mail_ids = mail_ids[-limit_per_folder:] 
                
                for mail_id in mail_ids:
                    # On utilise BODY.PEEK[] pour lire le mail SANS enlever le drapeau UNSEEN !
                    status, msg_data = self.mail.uid('fetch', mail_id, '(BODY.PEEK[])')
                    if status != 'OK':
                        continue

                    mail_obj = self._parse_email_from_bytes(mail_id, msg_data)
                    if mail_obj:
                        emails_list.append(mail_obj)

            logger.info(f"{len(emails_list)} e-mail(s) UNSEEN trouvé(s) au total dans l'arborescence.")
            return emails_list

        except Exception as e:
            logger.error(f"Erreur lors du scan global des e-mails non lus : {e}")
            raise IMAPError(f"Erreur IMAP globale : {e}")


    def _parse_email_from_bytes(self, mail_id: bytes, msg_data: list) -> Optional[MailObject]:
        """
        Méthode utilitaire privée pour extraire et formater un objet MailObject 
        à partir des données brutes renvoyées par la commande IMAP fetch.
        """
        import email
        from email import policy
        import email.utils
        from datetime import datetime
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1], policy=policy.default)
                
                sujet = str(msg.get('subject', '(Sans objet)'))
                
                # Nettoyage de l'expéditeur
                raw_expediteur = str(msg.get('from', ''))
                extracted_email = extract_email_address(raw_expediteur)
                expediteur = extracted_email if extracted_email else '(Expéditeur inconnu)'
                
                # Parsing robuste de la date
                date_tuple = email.utils.parsedate_tz(msg.get('date'))
                if date_tuple:
                    timestamp = email.utils.mktime_tz(date_tuple)
                    date_reception = datetime.fromtimestamp(timestamp)
                else:
                    date_reception = datetime.now()

                # Extraction du contenu texte et des PJ
                contenu_texte = ""
                pieces_jointes = []
                contenu_pj_brut = "" # Variable pour stocker le texte brut des PJ

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                pieces_jointes.append(filename)
                                
                                # -- NOUVEAU : Tentative d'extraction du texte de la PJ --
                                texte_extrait = extract_text_from_attachment(part, filename)
                                if texte_extrait.strip():
                                    contenu_pj_brut += f"\n\n--- PIÈCE JOINTE : {filename} ---\n{texte_extrait}"
                        
                        # --- Prise en charge et nettoyage du HTML (Corps du mail) ---
                        elif content_type in ["text/plain", "text/html"] and "attachment" not in content_disposition:
                            try:
                                raw_text = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                                if content_type == "text/html":
                                    contenu_texte += clean_html_content(raw_text) + "\n"
                                else:
                                    contenu_texte += raw_text + "\n"
                            except Exception:
                                pass
                else:
                    try:
                        raw_payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                        if msg.get_content_type() == "text/html":
                            contenu_texte = clean_html_content(raw_payload)
                        else:
                            contenu_texte = raw_payload
                    except Exception:
                        contenu_texte = str(msg.get_payload())

                # Nettoyage final du texte principal
                contenu_final = contenu_texte.strip() or "(Contenu vide ou illisible)"
                
                # -- NOUVEAU : Troncature et fusion des pièces jointes --
                if contenu_pj_brut:
                    # On protège le LLM en forçant une limite stricte de tokens sur l'ensemble des PJ
                    contenu_pj_tronque = truncate_text_for_llm(contenu_pj_brut, max_tokens=1000)
                    contenu_final += contenu_pj_tronque

                # --- Estimation des tokens sur le total (Corps + PJ tronquées) ---
                nb_tokens = estimate_token_count(contenu_final)

                # Gestion sécurisée du décodage de l'ID IMAP
                id_str = mail_id.decode('utf-8') if isinstance(mail_id, bytes) else str(mail_id)

                # Instanciation de l'objet métier
                return MailObject(
                    id_mail=id_str,
                    date_reception=date_reception,
                    expediteur=expediteur,
                    sujet=sujet,
                    contenu_texte=contenu_final,
                    pieces_jointes=pieces_jointes,
                    nombre_tokens=nb_tokens
                )
                
        # Si la boucle se termine sans rien trouver
        return None

    async def fetch_unsynthesized_emails(self, limit_per_folder: int = 50) -> List[MailObject]:
        """
        Récupère tous les e-mails de la boîte (sauf corbeille) qui n'ont pas encore 
        été traités par le Pipeline C de synthèse nocturne.
        N'applique AUCUN flag pour respecter le principe d'acquittement (ACK).
        """
        async with self._lock:
            return await asyncio.to_thread(self._fetch_unsynthesized_emails_sync, limit_per_folder)

    def _fetch_unsynthesized_emails_sync(self, limit_per_folder: int) -> List[MailObject]:
        import re
        self._ensure_connected()

        logger.info("Récupération des e-mails non synthétisés (UNKEYWORD CopiloteSynthetise)...")
        emails_list = []
        
        try:
            status, folders = self.mail.list()
            if status != 'OK':
                raise IMAPError("Impossible de lister les dossiers de la messagerie.")

            for folder_data in folders:
                folder_str = folder_data.decode('utf-8')
                
                # Exclusion de la corbeille (adapter selon les noms usuels)
                if "trash" in folder_str.lower() or "corbeille" in folder_str.lower() or "deleted" in folder_str.lower():
                    continue

                # Extraction propre du nom du dossier IMAP
                match = re.search(r'\"([^\"]+)\"$', folder_str)
                if match:
                    folder_name = f'"{match.group(1)}"'
                else:
                    folder_name = folder_str.split()[-1]

                # Sélection en lecture seule (sécurité supplémentaire)
                status, _ = self.mail.select(folder_name, readonly=True)
                if status != 'OK':
                    continue

                # On cherche ceux qui n'ont PAS le tag CopiloteSynthetise
                status, messages = self.mail.uid('search', None, 'UNKEYWORD', 'CopiloteSynthetise')
                if status != 'OK' or not messages[0]:
                    continue

                mail_ids = messages[0].split()
                mail_ids = mail_ids[-limit_per_folder:] 
                
                for mail_id in mail_ids:
                    status, msg_data = self.mail.uid('fetch', mail_id, '(BODY.PEEK[])')
                    if status != 'OK':
                        continue

                    mail_obj = self._parse_email_from_bytes(mail_id, msg_data)
                    if mail_obj:
                        # Injection du dossier source pour permettre le marquage ultérieur
                        mail_obj.dossier_source = folder_name
                        emails_list.append(mail_obj)

            logger.info(f"{len(emails_list)} e-mail(s) en attente de synthèse récupéré(s).")
            return emails_list

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des e-mails pour la synthèse : {e}")
            raise IMAPError(f"Erreur IMAP globale (Synthèse) : {e}")


    async def mark_emails_as_synthesized(self, emails: List[MailObject]) -> bool:
        """
        Méthode d'Acquittement (ACK).
        Applique le flag 'CopiloteSynthetise' sur une liste d'e-mails pour qu'ils 
        ne soient plus traités lors des prochaines synthèses.
        """
        async with self._lock:
            return await asyncio.to_thread(self._mark_emails_as_synthesized_sync, emails)

    def _mark_emails_as_synthesized_sync(self, emails: List[MailObject]) -> bool:
        self._ensure_connected()
            
        if not emails:
            return True

        try:
            # 1. Regroupement intelligent des e-mails par dossier d'origine
            # Cela évite de faire des 'SELECT' intempestifs à chaque e-mail
            folders_dict = {}
            for mail in emails:
                folder = getattr(mail, 'dossier_source', '"INBOX"')
                if folder not in folders_dict:
                    folders_dict[folder] = []
                folders_dict[folder].append(mail.id_mail.encode('utf-8'))
                
            # 2. Itération par dossier et marquage par lots (Batching)
            for folder, uids in folders_dict.items():
                # On doit ouvrir le dossier en mode écriture (readonly=False)
                status, _ = self.mail.select(folder, readonly=False)
                if status != 'OK':
                    logger.warning(f"Impossible de sélectionner le dossier {folder} pour le marquage.")
                    continue
                    
                # Concaténation des UIDs séparés par une virgule pour une requête IMAP optimisée
                uids_str = b','.join(uids)
                status, _ = self.mail.uid('STORE', uids_str, '+FLAGS', 'CopiloteSynthetise')
                
                if status == 'OK':
                    logger.debug(f"{len(uids)} e-mail(s) marqué(s) 'CopiloteSynthetise' dans {folder}.")
                else:
                    logger.warning(f"Échec du marquage dans le dossier {folder}.")
                    
            return True
            
        except Exception as e:
            logger.error(f"Erreur critique lors du marquage des e-mails (ACK) : {e}")
            return False