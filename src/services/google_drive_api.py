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

from src.utils.logger import get_logger
from src.core.exceptions import GoogleAPIError


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
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service = None
        
        # Verrou pour s'assurer qu'on ne lit/écrit pas le même fichier en parallèle
        self._lock = asyncio.Lock()
        
        # Initialisation du logger avec le nom du module
        self.logger = get_logger(__name__)


    async def authenticate(self) -> None:
        """
        Vérifie la validité du token existant ou lance le flux d'authentification OAuth.
        Méthode asynchrone non-bloquante.
        """
        await asyncio.to_thread(self._authenticate_sync)

    def _authenticate_sync(self) -> None:
        """Logique synchrone d'authentification Google."""
        creds = None
        self.logger.debug("Vérification des tokens Google Drive...")

        # Chargement du token s'il existe
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            except Exception as e:
                self.logger.warning(f"Le fichier token.json est corrompu ou illisible : {e}")

        # Si pas de credentials valides, on authentifie
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Rafraîchissement du token Google Drive...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Échec du rafraîchissement du token : {e}")
                    raise GoogleAPIError("Impossible de rafraîchir le token Google Drive.")
            else:
                self.logger.info("Lancement du flux d'authentification OAuth local...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    self.logger.error(f"Erreur lors de l'authentification via credentials.json : {e}")
                    raise GoogleAPIError(f"Vérifiez votre fichier credentials.json : {e}")

            # Sauvegarde du nouveau token
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('drive', 'v3', credentials=creds)
            self.logger.info("Authentification Google Drive réussie.")
        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du service Drive : {e}")
            raise GoogleAPIError(f"Construction du service Drive échouée : {e}")

    async def find_file_or_folder(self, name: str, mime_type: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Recherche un fichier ou un dossier par son nom exact dans le Drive.
        """
        return await asyncio.to_thread(self._find_file_or_folder_sync, name, mime_type, parent_id)

    def _find_file_or_folder_sync(self, name: str, mime_type: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[str]:
        if not self.service:
            raise GoogleAPIError("Service Drive non authentifié. Appelez authenticate() d'abord.")

        query = f"name = '{name}' and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        self.logger.debug(f"Recherche Google Drive avec la requête : {query}")

        try:
            results = self.service.files().list(
                q=query, spaces='drive', fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            if not items:
                return None
            return items[0]['id']
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche Drive pour '{name}' : {e}")
            raise GoogleAPIError(f"Recherche Drive échouée : {e}")

    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Crée un nouveau dossier.
        """
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
            self.logger.info(f"Dossier '{folder_name}' créé avec succès (ID: {folder_id}).")
            return folder_id
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du dossier '{folder_name}' : {e}")
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

        self.logger.debug(f"Téléchargement du fichier ID {file_id}...")
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            content = fh.getvalue().decode('utf-8')
            self.logger.info(f"Contenu du fichier {file_id} téléchargé avec succès.")
            return content
        except Exception as e:
            self.logger.error(f"Erreur de téléchargement pour le fichier {file_id} : {e}")
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

        self.logger.debug(f"Mise à jour du fichier ID {file_id}...")
        try:
            # Création du flux binaire à partir du nouveau texte (pour le format Markdown .md)
            media_body = MediaIoBaseUpload(
                io.BytesIO(new_content.encode('utf-8')), 
                mimetype='text/markdown', 
                resumable=True
            )
            
            # Appel à l'API pour mettre à jour
            self.service.files().update(
                fileId=file_id,
                media_body=media_body
            ).execute()
            
            self.logger.info(f"Fichier {file_id} écrasé et mis à jour avec succès.")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la mise à jour du fichier {file_id} : {e}")
            raise GoogleAPIError(f"Mise à jour Drive échouée : {e}")