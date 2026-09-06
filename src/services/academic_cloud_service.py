import os
import tempfile
import zipfile
import asyncio
import requests
from typing import List, Tuple

from src.core.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AcademicCloudService:
    """
    Service dédié à l'interaction avec le cloud académique (Nextcloud).
    Gère le téléchargement d'archives ZIP et leur extraction sur le SSD.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        # On s'assure que l'URL se termine bien par /download pour forcer le ZIP
        base_url = self.settings.ACADEMIC_CLOUD_URL.rstrip('/')
        if not base_url.endswith('download'):
            self.download_url = f"{base_url}/download"
        else:
            self.download_url = base_url
            
        self._lock = asyncio.Lock()
        logger.debug("AcademicCloudService initialisé.")

    async def download_and_extract(self) -> Tuple[str, List[str]]:
        """
        Télécharge le ZIP depuis le cloud académique et l'extrait localement.
        Méthode asynchrone pour ne pas bloquer l'Event Loop.
        
        Returns:
            Tuple[str, List[str]]: (Chemin du dossier temporaire racine, Liste des chemins complets vers les fichiers extraits)
        """
        async with self._lock:
            return await asyncio.to_thread(self._download_and_extract_sync)

    def _download_and_extract_sync(self) -> Tuple[str, List[str]]:
        """Logique synchrone de téléchargement et d'extraction isolée dans un thread."""
        logger.info(f"Début du téléchargement de l'archive depuis {self.download_url}")
        
        # 1. Création d'un dossier temporaire sécurisé géré par l'OS
        temp_dir = tempfile.mkdtemp(prefix="copilote_cloud_")
        zip_path = os.path.join(temp_dir, "archive.zip")
        extracted_files = []

        try:
            # 2. Téléchargement en mode streaming pour préserver la RAM
            with requests.get(self.download_url, stream=True, timeout=60) as response:
                response.raise_for_status()
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.debug(f"Archive téléchargée avec succès sur le SSD : {zip_path}")
            
            # 3. Extraction de l'archive ZIP
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as archive:
                archive.extractall(extract_dir)
                
            logger.info("Extraction de l'archive terminée.")
            
            # 4. Parcours récursif pour lister tous les fichiers extraits
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    extracted_files.append(full_path)
                    
            return temp_dir, extracted_files
            
        except Exception as e:
            logger.error(f"Échec lors de la récupération ou de l'extraction du cloud académique : {e}", exc_info=True)
            # En cas d'échec on s'assure de nettoyer les éventuels résidus
            self._cleanup_temp_dir_sync(temp_dir)
            raise RuntimeError(f"Erreur du service cloud académique : {e}")

    async def cleanup(self, temp_dir: str) -> None:
        """
        Supprime le dossier temporaire et tout son contenu du SSD.
        """
        async with self._lock:
            await asyncio.to_thread(self._cleanup_temp_dir_sync, temp_dir)

    def _cleanup_temp_dir_sync(self, temp_dir: str) -> None:
        import shutil
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Dossier temporaire {temp_dir} supprimé avec succès.")
        except Exception as e:
            logger.warning(f"Impossible de supprimer le dossier temporaire {temp_dir} : {e}")