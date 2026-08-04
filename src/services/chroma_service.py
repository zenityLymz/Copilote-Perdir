import asyncio
from typing import List, Dict, Any, Optional

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

from google import genai
from google.genai import types

from src.core import MailObject, ChromaDBError, get_settings
from src.utils import get_logger


class CustomGeminiEmbeddingFunction(EmbeddingFunction):
    """
    Fonction d'embedding personnalisée utilisant le nouveau SDK google-genai,
    pour contourner le bug interne de ChromaDB.
    """
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=input,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        # On extrait les valeurs vectorielles de la réponse pour ChromaDB
        return [emb.values for emb in response.embeddings]

class ChromaDBService:
    """
    Gère la base de données vectorielle locale hébergée physiquement sur le Raspberry Pi.
    Responsable du stockage des embeddings pour la recherche RAG sémantique.
    """


    def __init__(self, persist_directory: str, embedding_model_name: Optional[str] = None) -> None:
        """
        Initialise la connexion à la base de données ChromaDB en mode persistant.

        Args:
            persist_directory (str): Le chemin absolu ou relatif vers le dossier `data/chroma_db/`.
            embedding_model_name (str): Le nom du modèle d'embedding de l'API Google à utiliser.
        """
        self.persist_directory = persist_directory
        self.logger = get_logger(__name__)
        self._lock = asyncio.Lock()
        
        try:
            # Récupération de la configuration
            settings = get_settings()
            api_key = settings.GEMINI_API_KEY

            # Si aucun nom de modèle n'est fourni, on utilise celui défini dans la configuration
            self.embedding_model_name = embedding_model_name or settings.EMBEDDING_MODEL_NAME
            
            # Initialisation du client persistant local
            self.client = chromadb.PersistentClient(path=self.persist_directory)
                        
            # Nouvelle configuration de la fonction d'embedding
            self.embedding_function = CustomGeminiEmbeddingFunction(
                api_key=api_key,
                model_name=self.embedding_model_name
            )
            
            # Création ou récupération de la collection principale dédiée aux emails
            self.collection = self.client.get_or_create_collection(
                name="emails",
                embedding_function=self.embedding_function
            )
            
            self.logger.info("Service ChromaDB initialisé avec succès en mode persistant.")
        except Exception as e:
            self.logger.error(f"Échec de l'initialisation de ChromaDB : {e}")
            raise ChromaDBError(f"Erreur d'initialisation de la base vectorielle : {e}")

    async def index_emails(self, emails: List[MailObject]) -> None:
        """
        Convertit une liste d'e-mails en embeddings vectoriels et les stocke dans la collection.
        Méthode asynchrone pour ne pas bloquer l'Event Loop.

        Args:
            emails (List[MailObject]): Les objets mails à indexer.
        """
        if not emails:
            return
            
        async with self._lock:
            await asyncio.to_thread(self._index_emails_sync, emails)

    def _index_emails_sync(self, emails: List[MailObject]) -> None:
        """Logique synchrone d'indexation déléguée dans un thread."""
        ids = []
        documents = []
        metadatas = []
        
        for mail in emails:
            ids.append(mail.id_mail)
            documents.append(mail.contenu_texte)
            
            # Préparation des métadonnées (ChromaDB n'accepte que str, int, float, bool)
            pieces_jointes_str = ", ".join(mail.pieces_jointes) if mail.pieces_jointes else ""
            
            metadatas.append({
                "expediteur": mail.expediteur,
                "sujet": mail.sujet,
                "date_reception": mail.date_reception.isoformat(),
                "pieces_jointes": pieces_jointes_str,
                "traite": mail.est_traite
            })
            
        try:
            self.logger.debug(f"Tentative d'indexation (upsert) de {len(emails)} e-mail(s)...")
            self.collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            self.logger.info(f"{len(emails)} e-mail(s) correctement indexé(s) dans ChromaDB.")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'indexation dans ChromaDB : {e}")
            raise ChromaDBError(f"L'indexation a échoué : {e}")

    async def search_semantic(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Recherche les e-mails les plus pertinents sémantiquement par rapport à une requête.
        Méthode asynchrone non-bloquante.

        Args:
            query (str): La question ou recherche de l'utilisateur.
            n_results (int): Le nombre maximum de résultats à retourner.
            filter_metadata (Optional[Dict]): Filtres optionnels (ex: expéditeur, date).

        Returns:
            List[Dict]: Les documents trouvés, incluant le texte d'origine, les distances et les métadonnées.
        """
        async with self._lock:
            return await asyncio.to_thread(self._search_semantic_sync, query, n_results, filter_metadata)

    def _search_semantic_sync(self, query: str, n_results: int, filter_metadata: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Logique synchrone de requête (RAG)."""
        try:
            self.logger.debug(f"Recherche ChromaDB pour la requête : '{query}'")
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_metadata
            )
            
            formatted_results = []
            
            # Vérifie que la recherche a retourné des données structurellement valides
            if results and results.get("ids") and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None
                    })
                    
            self.logger.info(f"Recherche sémantique terminée : {len(formatted_results)} résultat(s) trouvé(s).")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche vectorielle : {e}")
            raise ChromaDBError(f"La requête sémantique a échoué : {e}")

    async def delete_email(self, mail_id: str) -> bool:
        """
        Supprime les embeddings d'un e-mail spécifique de la base vectorielle.
        Méthode asynchrone non-bloquante.

        Args:
            mail_id (str): L'identifiant unique (ID IMAP) de l'e-mail à purger.

        Returns:
            bool: True si la suppression a réussi, False sinon.
        """
        async with self._lock:
            return await asyncio.to_thread(self._delete_email_sync, mail_id)

    def _delete_email_sync(self, mail_id: str) -> bool:
        """Logique synchrone de suppression dans la collection."""
        try:
            self.logger.debug(f"Tentative de suppression de l'e-mail ID {mail_id} de la base.")
            self.collection.delete(ids=[mail_id])
            self.logger.info(f"E-mail {mail_id} purgé avec succès de ChromaDB.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression de l'e-mail {mail_id} : {e}")
            # On loggue l'erreur mais on ne crashe pas le système entier (par ex. si le mail n'existait pas)
            return False