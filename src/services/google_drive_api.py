from typing import Optional, List, Dict, Any
import os
import io
import asyncio
from typing import Optional, List, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from src.utils import get_logger
from src.core import GoogleAPIError

# Initialisation du logger pour ce module
logger = get_logger(__name__)

class GoogleDriveService:
    """
    Gère l'authentification OAuth 2.0 et les opérations sur l'espace Google Drive.
    """

    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json") -> None:
        """
        Initialise le service Drive avec gestion sécurisée des tokens OAuth et un verrou pour les écritures.

        Args:
            credentials_path (str): Chemin vers le fichier credentials.json fourni par GCP.
            token_path (str): Chemin pour stocker le token de rafraîchissement local.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/tasks'
        ]
        self.service = None
        
        # Verrou pour s'assurer qu'on ne lit/écrit pas le même fichier en parallèle
        self._lock = asyncio.Lock()


    async def authenticate(self) -> None:
        """
        Vérifie la validité du token existant ou lance le flux d'authentification OAuth.
        Méthode asynchrone non-bloquante.
        """
        await asyncio.to_thread(self._authenticate_sync)

    def _authenticate_sync(self) -> None:
        """Logique synchrone d'authentification Google avec protection Headless."""
        creds = None
        logger.debug("Vérification des tokens Google Drive...")

        # Chargement du token s'il existe
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            except Exception as e:
                logger.warning(f"Le fichier token.json est corrompu ou illisible : {e}")

        # Si pas de credentials valides, on authentifie
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Rafraîchissement du token Google Drive...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Échec du rafraîchissement du token : {e}")
                    raise GoogleAPIError("Le token a expiré de manière irrévocable (ou a été révoqué).")
            else:
                # --- NOUVEAU : Protection Anti-Figeage (Headless) ---
                # Si on est sur Linux (posix) et qu'il n'y a pas de variable DISPLAY (pas d'écran)
                if os.name == 'posix' and 'DISPLAY' not in os.environ:
                    logger.critical(
                        "🔒 ENVIRONNEMENT SANS ÉCRAN DÉTECTÉ (Headless).\n"
                        "Le programme refuse de lancer le navigateur web pour éviter de se figer.\n"
                        "💡 SOLUTION : Lancez l'application sur votre PC, connectez-vous à Google, "
                        "puis transférez le fichier 'token.json' généré sur ce Raspberry Pi."
                    )
                    raise GoogleAPIError("Authentification initiale impossible sur un serveur sans interface graphique.")
                
                logger.info("Lancement du flux d'authentification OAuth local (Navigateur requis)...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Erreur lors de l'authentification via credentials.json : {e}")
                    raise GoogleAPIError(f"Vérifiez votre fichier credentials.json : {e}")

            # Sauvegarde du nouveau token
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Authentification Google Drive réussie.")
        except Exception as e:
            logger.error(f"Erreur lors de la construction du service Drive : {e}")
            raise GoogleAPIError(f"Construction du service Drive échouée : {e}")

    async def find_file_or_folder(self, name: str, mime_type: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Recherche un fichier ou un dossier par son nom exact dans le Drive.
        """
        async with self._lock:
            return await asyncio.to_thread(self._find_file_or_folder_sync, name, mime_type, parent_id)

    def _find_file_or_folder_sync(self, name: str, mime_type: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[str]:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié. Appelez authenticate() d'abord.")

        query = f"name = '{name}' and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        logger.debug(f"Recherche Google Drive avec la requête : {query}")

        try:
            results = self.service.files().list(
                q=query, spaces='drive', fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if not items:
                return None
            return items[0]['id']
        except Exception as e:
            logger.error(f"Erreur lors de la recherche Drive pour '{name}' : {e}")
            raise GoogleAPIError(f"Recherche Drive échouée : {e}")

    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Crée un nouveau dossier.
        """
        async with self._lock:
            return await asyncio.to_thread(self._create_folder_sync, folder_name, parent_id)

    def _create_folder_sync(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            folder_id = file.get('id')
            logger.info(f"Dossier '{folder_name}' créé avec succès (ID: {folder_id}).")
            return folder_id
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier '{folder_name}' : {e}")
            raise GoogleAPIError(f"Création de dossier échouée : {e}")

    async def download_file_content(self, file_id: str) -> str:
        """
        Télécharge le contenu textuel brut d'un fichier hébergé sur Drive (ex: .md, .txt).
        Sert à l'étape 'Read' de la mécanique Read-Rewrite-Replace.
        """
        async with self._lock:
            return await asyncio.to_thread(self._download_file_content_sync, file_id)

    def _download_file_content_sync(self, file_id: str) -> str:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")

        logger.debug(f"Téléchargement du fichier ID {file_id}...")
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            content = fh.getvalue().decode('utf-8')
            logger.info(f"Contenu du fichier {file_id} téléchargé avec succès.")
            return content
        except Exception as e:
            logger.error(f"Erreur de téléchargement pour le fichier {file_id} : {e}")
            raise GoogleAPIError(f"Téléchargement Drive échoué : {e}")

    async def update_file_content(self, file_id: str, new_content: str) -> bool:
        """
        Écrase intégralement le contenu d'un fichier existant sur Drive avec de nouvelles données.
        Sert à l'étape 'Replace' après le travail de l'agent de synthèse.
        """
        async with self._lock:
            return await asyncio.to_thread(self._update_file_content_sync, file_id, new_content)

    def _update_file_content_sync(self, file_id: str, new_content: str) -> bool:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")

        logger.debug(f"Mise à jour du fichier ID {file_id}...")
        try:
            # Création du flux binaire avec le mimetype HTML natif
            media_body = MediaIoBaseUpload(
                io.BytesIO(new_content.encode('utf-8')), 
                mimetype='text/html', 
                resumable=True
            )
            
            # Appel à l'API pour mettre à jour
            self.service.files().update(
                fileId=file_id,
                media_body=media_body
            ).execute()
            
            logger.info(f"Fichier Google Doc {file_id} écrasé et mis à jour avec succès.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du fichier {file_id} : {e}")
            raise GoogleAPIError(f"Mise à jour Drive échouée : {e}")



    async def search_files_by_content(self, query_string: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Recherche plein texte dans le Drive. Retourne l'ID, le nom, le type et le lien d'accès.
        """
        async with self._lock:
            return await asyncio.to_thread(self._search_files_by_content_sync, query_string, limit)

    def _search_files_by_content_sync(self, query_string: str, limit: int) -> List[Dict[str, Any]]:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")
        
        # Opérateur 'fullText contains' pour chercher dans le contenu des documents
        query = f"fullText contains '{query_string}' and trashed = false"
        logger.debug(f"Recherche plein texte Drive : {query}")
        
        try:
            results = self.service.files().list(
                q=query,
                pageSize=limit,
                # On demande explicitement webViewLink pour que le Perdir puisse cliquer dessus
                fields="nextPageToken, files(id, name, mimeType, webViewLink)",
                orderBy="modifiedTime desc" 
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            logger.error(f"Erreur lors de la recherche plein texte Drive : {e}")
            raise GoogleAPIError(f"Recherche plein texte échouée : {e}")

    async def get_file_text_content(self, file_id: str, mime_type: str) -> str:
        """
        Exporte (Google Docs) ou télécharge (Fichiers bruts) le contenu au format texte.
        """
        async with self._lock:
            return await asyncio.to_thread(self._get_file_text_content_sync, file_id, mime_type)

    def _get_file_text_content_sync(self, file_id: str, mime_type: str) -> str:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")
        
        try:
            # Traitement spécifique selon la nature du fichier
            if 'application/vnd.google-apps.document' in mime_type:
                request = self.service.files().export_media(fileId=file_id, mimeType='text/plain')
            elif 'text/plain' in mime_type or 'text/markdown' in mime_type:
                request = self.service.files().get_media(fileId=file_id)
            else:
                raise ValueError(f"Type de fichier non supporté pour l'extraction : {mime_type}")

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return fh.getvalue().decode('utf-8')
        except ValueError as ve:
            raise ve
        except Exception as e:
            logger.error(f"Erreur d'extraction de texte pour {file_id} : {e}")
            raise GoogleAPIError(f"Extraction de texte échouée : {e}")

    async def export_google_doc_as_html(self, file_id: str) -> str:
        """
        Exporte un document Google Docs natif au format HTML brut.
        Sert à la nouvelle étape 'Read' de la mécanique Read-Rewrite-Replace pour la Mémoire.
        """
        async with self._lock:
            return await asyncio.to_thread(self._export_google_doc_as_html_sync, file_id)

    def _export_google_doc_as_html_sync(self, file_id: str) -> str:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié.")

        logger.debug(f"Export HTML du Google Doc ID {file_id}...")
        try:
            # On utilise export_media avec le mimeType text/html (Spécifique aux Google Docs)
            request = self.service.files().export_media(fileId=file_id, mimeType='text/html')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            content = fh.getvalue().decode('utf-8')
            logger.info(f"Contenu HTML du Google Doc {file_id} exporté avec succès.")
            return content
        except Exception as e:
            logger.error(f"Erreur d'export HTML pour le document {file_id} : {e}")
            raise GoogleAPIError(f"Export HTML Drive échoué : {e}")