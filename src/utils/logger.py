import logging
from pathlib import Path
from typing import Optional

def setup_logger(log_file_path: Optional[Path] = None, log_level: int = logging.INFO) -> None:
    """
    Configure le système de journalisation (logging) global de l'application.
    
    Cette fonction doit être appelée au démarrage du démon principal (main.py).
    Elle configure un format standardisé et permet de rediriger les logs
    vers la console et/ou un fichier physique (indispensable pour le 
    débogage sur le Raspberry Pi).

    Args:
        log_file_path (Optional[Path]): Chemin vers le fichier d'écriture des logs. 
                                        Si None, journalise uniquement dans la console.
        log_level (int): Niveau de sévérité minimal à enregistrer (ex: logging.INFO, logging.DEBUG).
    """
    pass

def get_logger(module_name: str) -> logging.Logger:
    """
    Instancie et retourne un logger spécifique pour un module donné.
    
    Permet une traçabilité granulaire (savoir de quel module provient l'erreur).

    Args:
        module_name (str): Nom du module appelant (utiliser généralement `__name__`).

    Returns:
        logging.Logger: L'instance du logger prête à être utilisée dans le module.
    """
    pass