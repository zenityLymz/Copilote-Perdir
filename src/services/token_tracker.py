import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TokenTrackerService:
    """
    Service gérant le suivi de la consommation de l'API Gemini.
    Utilise une base de données locale SQLite pour garantir l'intégrité des données 
    lors d'écritures asynchrones concurrentes.
    """

    def __init__(self, db_path: str = "data/token_usage.db") -> None:
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialise la base de données et crée la table si elle n'existe pas."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        model_name TEXT NOT NULL,
                        input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        action_context TEXT
                    )
                ''')
                conn.commit()
            logger.debug("Base de données de tracking des tokens initialisée.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la DB de tracking : {e}")

    async def log_usage(self, model_name: str, input_tokens: int, output_tokens: int, action_context: str = "Inconnu") -> None:
        """
        Enregistre une consommation de tokens de manière asynchrone.
        """
        total_tokens = input_tokens + output_tokens
        
        # On utilise to_thread pour ne pas bloquer l'Event Loop lors de l'écriture disque
        async with self._lock:
            await asyncio.to_thread(
                self._log_usage_sync, 
                model_name, input_tokens, output_tokens, total_tokens, action_context
            )

    def _log_usage_sync(self, model_name: str, in_t: int, out_t: int, tot_t: int, context: str) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO usage_logs (model_name, input_tokens, output_tokens, total_tokens, action_context)
                    VALUES (?, ?, ?, ?, ?)
                ''', (model_name, in_t, out_t, tot_t, context))
                conn.commit()
        except Exception as e:
            logger.error(f"Échec de l'enregistrement des tokens : {e}")

    async def get_stats(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques de consommation regroupées par modèle sur une période donnée.
        """
        if not end_date:
            end_date = datetime.now()
            
        async with self._lock:
            return await asyncio.to_thread(self._get_stats_sync, start_date, end_date)

    def _get_stats_sync(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        stats = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Requête SQL pour sommer les tokens par modèle
                cursor.execute('''
                    SELECT model_name, SUM(input_tokens), SUM(output_tokens), SUM(total_tokens)
                    FROM usage_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                    GROUP BY model_name
                ''', (start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S")))
                
                rows = cursor.fetchall()
                
                for row in rows:
                    stats[row[0]] = {
                        "input": row[1],
                        "output": row[2],
                        "total": row[3]
                    }
            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques : {e}")
            return {}

    async def get_action_stats(self, start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Récupère les statistiques d'utilisation regroupées par grande fonction (ex: Triage, Synthese)
        et séparées entre facturation 'gratuit' et 'payant'.
        """
        if not end_date:
            end_date = datetime.now()
            
        async with self._lock:
            return await asyncio.to_thread(self._get_action_stats_sync, start_date, end_date)

    def _get_action_stats_sync(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        stats = {
            "gratuit": {"total": 0, "actions": {}},
            "payant": {"total": 0, "actions": {}}
        }
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT model_name, action_context, total_tokens
                    FROM usage_logs
                    WHERE timestamp >= ? AND timestamp <= ?
                ''', (start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S")))
                
                for row in cursor.fetchall():
                    model, action, tokens = row
                    
                    # 1. Extraction de la fonction métier (ex: "Triage_Mail_123" -> "Triage")
                    fonction = action.split('_')[0] if action else "Autre"
                    
                    # 2. Séparation Gratuit / Payant
                    categorie = "gratuit" if "gratuit" in model.lower() else "payant"
                    
                    if fonction not in stats[categorie]["actions"]:
                        stats[categorie]["actions"][fonction] = 0
                        
                    # 3. Cumul des tokens
                    stats[categorie]["actions"][fonction] += tokens
                    stats[categorie]["total"] += tokens
                    
            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats par action : {e}")
            return stats