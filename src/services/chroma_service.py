from typing import List, Dict, Any, Optional
from src.core.models import MailObject

class ChromaDBService:
    """
    Gère la base de données vectorielle locale hébergée physiquement sur le Raspberry Pi.
    Responsable du stockage des embeddings pour la recherche RAG sémantique.
    """

    def __init__(self, persist_directory: str, embedding_model_name: str = "models/text-embedding-004") -> None:
        """
        Initialise la connexion à la base de données ChromaDB en mode persistant.

        Args:
            persist_directory (str): Le chemin absolu ou relatif vers le dossier `data/chroma_db/`.
            embedding_model_name (str): Le nom du modèle d'embedding de l'API Google à utiliser.
        """
        pass

    def index_emails(self, emails: List[MailObject]) -> None:
        """
        Convertit une liste d'e-mails en embeddings vectoriels et les stocke dans la collection.

        Args:
            emails (List[MailObject]): Les objets mails à indexer.
        """
        pass

    def search_semantic(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Recherche les e-mails les plus pertinents sémantiquement par rapport à une requête en langage naturel.

        Args:
            query (str): La question ou recherche de l'utilisateur.
            n_results (int): Le nombre maximum de résultats à retourner.
            filter_metadata (Optional[Dict]): Filtres optionnels (ex: expéditeur, date).

        Returns:
            List[Dict]: Les documents trouvés, incluant le texte d'origine, les distances et les métadonnées.
        """
        pass

    def delete_email(self, mail_id: str) -> bool:
        """
        Supprime les embeddings d'un e-mail spécifique de la base vectorielle.
        Permet de purger les données si le mail est supprimé de la source IMAP.

        Args:
            mail_id (str): L'identifiant unique (ID IMAP) de l'e-mail à purger.

        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        pass