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
from src.utils.logger import get_logger

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
        logger.debug("Service IMAP initialisé avec la configuration centrale.")


    async def connect(self) -> None:
        """Point d'entrée asynchrone pour la connexion IMAP."""
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


    async def fetch_unread_emails(self, folder: str = "INBOX", limit: int = 50) -> List[MailObject]:
        """Point d'entrée asynchrone pour relever les e-mails non lus."""
        return await asyncio.to_thread(self._fetch_unread_emails_sync, folder, limit)

    def _fetch_unread_emails_sync(self, folder: str, limit: int) -> List[MailObject]:
        """Logique métier d'extraction et de parsing des mails."""
        if not self.mail:
            raise IMAPError("Service IMAP non connecté.")

        logger.info(f"Recherche de nouveaux messages (UNSEEN) dans le dossier '{folder}'...")
        try:
            status, _ = self.mail.select(f'"{folder}"')
            if status != 'OK':
                raise IMAPError(f"Dossier introuvable ou inaccessible : {folder}")

            status, messages = self.mail.uid('search', None, 'UNSEEN')
            if status != 'OK' or not messages[0]:
                logger.info("Aucun nouveau message trouvé.")
                return []

            mail_ids = messages[0].split()
            mail_ids = mail_ids[:limit]
            emails_list = []
            
            for mail_id in mail_ids:
                status, msg_data = self.mail.uid('fetch', mail_id, '(RFC822)')
                if status != 'OK':
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1], policy=policy.default)
                        
                        sujet = str(msg.get('subject', '(Sans objet)'))
                        expediteur = str(msg.get('from', '(Expéditeur inconnu)'))
                        
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
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                
                                if "attachment" in content_disposition:
                                    filename = part.get_filename()
                                    if filename:
                                        pieces_jointes.append(filename)
                                elif content_type == "text/plain" and "attachment" not in content_disposition:
                                    try:
                                        contenu_texte += part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                                    except Exception:
                                        pass
                        else:
                            try:
                                contenu_texte = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='replace')
                            except Exception:
                                contenu_texte = str(msg.get_payload())

                        mail_obj = MailObject(
                            id_mail=mail_id.decode('utf-8'),
                            date_reception=date_reception,
                            expediteur=expediteur,
                            sujet=sujet,
                            contenu_texte=contenu_texte.strip() or "(Contenu vide ou illisible)",
                            pieces_jointes=pieces_jointes
                        )
                        emails_list.append(mail_obj)

            logger.info(f"{len(emails_list)} e-mail(s) non lu(s) récupéré(s) et formaté(s).")
            return emails_list

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des e-mails : {e}")
            raise IMAPError(f"Erreur lors de la récupération des e-mails : {e}")
    

    async def move_email(self, decision: TriDecision) -> bool:
        """Déplace un e-mail de manière asynchrone."""
        return await asyncio.to_thread(self._move_email_sync, decision)

    def _move_email_sync(self, decision: TriDecision) -> bool:
        """Exécute les commandes IMAP COPY et STORE pour déplacer l'e-mail."""
        if not self.mail:
            logger.error("Déplacement impossible : IMAP non connecté.")
            return False
            
        try:
            uid_mail = decision.id_mail.encode('utf-8')
            target_folder = f'"{decision.dossier_cible}"'
            
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

    async def mark_as_read(self, mail_id: str) -> bool:
        """Marque un e-mail comme lu de manière asynchrone."""
        return await asyncio.to_thread(self._mark_as_read_sync, mail_id)

    def _mark_as_read_sync(self, mail_id: str) -> bool:
        """Logique IMAP de marquage \\Seen."""
        if not self.mail:
            return False
            
        try:
            uid_mail = mail_id.encode('utf-8')
            status, _ = self.mail.uid('STORE', uid_mail, '+FLAGS', '(\\Seen)')
            success = (status == 'OK')
            if success:
                logger.debug(f"E-mail {mail_id} marqué comme lu.")
            return success
        except Exception as e:
            logger.error(f"Erreur lors du marquage comme lu de l'e-mail {mail_id} : {e}")
            return False
