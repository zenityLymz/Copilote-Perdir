from typing import List, Optional
from src.core.models import MailObject, TriDecision

class IMAPService:
    """
    Gère la connexion et les opérations sur la boîte de messagerie académique via le protocole IMAP.
    """

    def __init__(self, host: str, user: str, password: str, port: int = 993) -> None:
        """
        Initialise les paramètres de connexion au serveur IMAP.

        Args:
            host (str): L'adresse du serveur IMAP (ex: imap.ac-lyon.fr).
            user (str): L'identifiant de connexion.
            password (str): Le mot de passe ou mot de passe d'application.
            port (int): Le port sécurisé (993 par défaut).
        """
        pass

    def connect(self) -> None:
        """
        Établit la connexion sécurisée avec le serveur IMAP et s'authentifie.
        Lève une IMAPError en cas d'échec.
        """
        pass

    def fetch_unread_emails(self, folder: str = "INBOX", limit: int = 50) -> List[MailObject]:
        """
        Récupère les e-mails non lus depuis un dossier spécifique et les formate.

        Args:
            folder (str): Le dossier cible (INBOX par défaut).
            limit (int): Nombre maximum d'e-mails à récupérer en une fois.

        Returns:
            List[MailObject]: Une liste d'objets MailObject strictement typés.
        """
        pass

    def move_email(self, decision: TriDecision) -> bool:
        """
        Déplace un e-mail vers un sous-dossier physique suite à la décision de l'IA.

        Args:
            decision (TriDecision): L'objet contenant l'id du mail et le dossier cible.

        Returns:
            bool: True si le déplacement a réussi, False sinon.
        """
        pass

    def mark_as_read(self, mail_id: str) -> bool:
        """
        Marque un e-mail spécifique comme lu sur le serveur.

        Args:
            mail_id (str): L'identifiant unique de l'e-mail.

        Returns:
            bool: True si l'opération a réussi.
        """
        pass

    def disconnect(self) -> None:
        """
        Ferme proprement la connexion avec le serveur IMAP.
        """
        pass