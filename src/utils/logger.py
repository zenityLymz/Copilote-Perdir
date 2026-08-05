import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logger(log_file_path: Optional[Path] = None, log_level: int = logging.INFO) -> None:
    """
    Configure le système de journalisation (logging) global de l'application.
    
    Cette fonction utilise un RotatingFileHandler pour limiter la taille des fichiers
    de logs (ex: 5 Mo) afin d'éviter la saturation de la RAM lors de la lecture,
    tout en conservant un historique glissant.

    Args:
        log_file_path (Optional[Path]): Chemin vers le fichier d'écriture des logs. 
                                        Si None, journalise uniquement dans la console.
        log_level (int): Niveau de sévérité minimal à enregistrer (ex: logging.INFO, logging.DEBUG).
    """
    # Définition d'un format standardisé et professionnel
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # Récupération du logger racine (root)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Nettoyage des handlers existants pour éviter la duplication des logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Configuration du Handler pour la console (sortie standard)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Configuration du Handler pour le fichier physique avec ROTATION
    if log_file_path:
        # S'assurer que le dossier parent existe avant de créer le fichier
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Rotation par taille : 5 Mo maximum par fichier (5 * 1024 * 1024 octets)
        # backupCount=5 signifie qu'il gardera app.log, app.log.1, jusqu'à app.log.5
        file_handler = RotatingFileHandler(
            filename=log_file_path, 
            mode='a',
            maxBytes=5 * 1024 * 1024, 
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Réduire au silence les bibliothèques externes très bavardes
    # On force leur niveau à WARNING, ainsi elles ne loggeront que les vraies erreurs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

def get_logger(module_name: str) -> logging.Logger:
    """
    Instancie et retourne un logger spécifique pour un module donné.
    
    Permet une traçabilité granulaire (savoir de quel module provient l'erreur).

    Args:
        module_name (str): Nom du module appelant (utiliser généralement `__name__`).

    Returns:
        logging.Logger: L'instance du logger prête à être utilisée dans le module.
    """
    return logging.getLogger(module_name)