"""
Point d'entrée principal (Main) du Copilote IA pour Personnel de Direction.

Ce script initialise la configuration, connecte les services (IMAP, Google Drive, ChromaDB, Telegram),
instancie les agents (Gemini) et lance les trois pipelines (A, B, C) de manière totalement asynchrone.
"""

import asyncio
import os
import logging
from datetime import datetime
from pathlib import Path

from src.core.config import get_settings
from src.core.dependencies import (
    set_imap_service,
    get_imap_service,
    set_chroma_service,
    set_drive_service,
    set_telegram_service,
    set_token_tracker_service,
    get_token_tracker_service,
    set_gemini_router_service
)
from src.utils.logger import setup_logger, get_logger

from src.services import (
    IMAPService,
    ChromaDBService,
    GoogleDriveService,
    TelegramBotService,
    TokenTrackerService,
    GeminiRouterService
)
from src.agents import (
    TriageAgent,
    OrchestratorAgent,
    SynthAgent
)
from src.workflows import (
    PipelineAMails,
    PipelineBTelegram,
    PipelineCSynthesis
)

from telegram import Update
from telegram.ext import ContextTypes

# Configuration initiale du logging avec rotation de fichier (max 5 Mo) pour le Raspberry Pi
LOG_FILE = Path("data/logs/copilote.log")
setup_logger(log_file_path=LOG_FILE, log_level=logging.INFO)
logger = get_logger("MainApp")

async def run_pipeline_a_loop(pipeline_a: PipelineAMails, interval_seconds: int = 300) -> None:
    """
    Boucle infinie pour exécuter le Pipeline A (Triage des Mails et Indexation) à intervalles réguliers.
    """
    logger.info("Démarrage de la tâche de fond : Pipeline A (Triage automatique & Indexation des envois).")
    while True:
        try:
            # 1. Traitement classique des e-mails entrants (Dossier de réception)
            await pipeline_a.run_pipeline(folder="INBOX", limit=50)
            
            # 2. Indexation silencieuse des e-mails envoyés par le Perdir
            await pipeline_a.index_sent_emails(folder="Sent", limit=50)
            
        except asyncio.CancelledError:
            logger.info("Arrêt de la boucle du Pipeline A.")
            break
        except Exception as e:
            # Sécurité défensive : Une erreur de relève IMAP ne doit jamais crasher la boucle
            logger.error(f"Erreur inattendue dans la boucle du Pipeline A : {e}", exc_info=True)
        
        # Pause asynchrone non-bloquante
        await asyncio.sleep(interval_seconds)

async def run_pipeline_c_loop(pipeline_c: PipelineCSynthesis, target_hour: int = 18) -> None:
    """
    Boucle infinie pour exécuter le Pipeline C (Synthèse Stratégique) une fois par jour.
    Persiste la date de dernière exécution sur le disque pour survivre aux coupures de courant.
    """
    logger.info(f"Démarrage de la tâche de fond : Pipeline C (Synthèse programmée à partir de {target_hour:02d}h00).")
    
    # Fichier d'état physique stocké dans le dossier data
    state_file = Path("data/last_synthesis.txt")
    last_run_date_str = None

    # Au démarrage, on essaie de lire la date de la dernière synthèse réussie
    if state_file.exists():
        try:
            last_run_date_str = state_file.read_text(encoding="utf-8").strip()
            logger.info(f"État restauré : dernière synthèse effectuée le {last_run_date_str}.")
        except Exception as e:
            logger.warning(f"Impossible de lire le fichier d'état de synthèse : {e}")

    while True:
        try:
            now = datetime.now()
            # On utilise le format ISO (YYYY-MM-DD) qui est parfait pour les comparaisons sous forme de chaîne de caractères
            current_date_str = now.date().isoformat()
            
            # Condition : Il est 18h ou plus ET la synthèse n'a pas encore été faite aujourd'hui
            if now.hour >= target_hour and last_run_date_str != current_date_str:
                logger.info(f"Fenêtre de synthèse atteinte (Il est {now.hour}h{now.minute:02d}). Déclenchement du Pipeline C.")
                
                # Exécution du pipeline
                await pipeline_c.run_pipeline()
                
                # Si le pipeline ne crashe pas, on valide l'exécution pour aujourd'hui
                last_run_date_str = current_date_str
                
                # Sauvegarde physique sur la carte SD du Raspberry
                try:
                    state_file.write_text(last_run_date_str, encoding="utf-8")
                    logger.info(f"Synthèse du {current_date_str} validée et sauvegardée sur le disque.")
                except Exception as e:
                    logger.error(f"Erreur lors de l'écriture du fichier d'état de synthèse : {e}")
                
            # Vérification toutes les 5 minutes
            await asyncio.sleep(300)
                
        except asyncio.CancelledError:
            logger.info("Arrêt de la boucle du Pipeline C.")
            break
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle du Pipeline C : {e}", exc_info=True)
            # En cas d'erreur de l'API Gemini, on attend 5 minutes avant la prochaine tentative
            await asyncio.sleep(300)

async def finance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande Telegram /finance pour afficher la consommation visuelle du mois en cours."""
    logger.info("Commande /finance demandée par le Perdir.")
    try:
        from src.core.config import get_settings
        settings = get_settings()
        tracker = get_token_tracker_service()
        now = datetime.now()
        
        # On remonte au 1er jour du mois actuel à 00:00:00
        premier_du_mois = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Récupération des données globales pour le calcul monétaire
        stats_mois = await tracker.get_stats(start_date=premier_du_mois)
        
        if not stats_mois:
            await update.message.reply_text("📊 <b>BILAN FINANCIER</b>\n\nAucune consommation enregistrée ce mois-ci.", parse_mode="HTML")
            return
            
        total_cost = 0.0
        for modele, data in stats_mois.items():
            in_t, out_t = data['input'], data['output']
            if "pro" in modele.lower():
                cost = (in_t * settings.PRICE_PRO_INPUT / 1000000) + (out_t * settings.PRICE_PRO_OUTPUT / 1000000)
            elif "lite" in modele.lower():
                cost = (in_t * settings.PRICE_FLASH_LITE_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_LITE_OUTPUT / 1000000)
            else:
                cost = (in_t * settings.PRICE_FLASH_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_OUTPUT / 1000000)
                
            total_cost += cost
            
        # --- Traduction manuelle du mois ---
        MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        mois_texte = MOIS_FR[now.month - 1]
        
        reponse = f"📊 <b>BILAN FINANCIER ({mois_texte} {now.year})</b>\n\n"
        reponse += f"💰 <b>Coût total estimé : ~{total_cost:.3f} $</b>\n"
        budget_restant = 10.0 - total_cost
        reponse += f"🏦 <b>Budget Google restant : ~{budget_restant:.3f} $</b>\n\n"

        # 2. Répartition VISUELLE par fonction (Gratuit vs Payant)
        action_stats = await tracker.get_action_stats(start_date=premier_du_mois)
        
        def format_bar(percent: float) -> str:
            """Génère une barre de progression ASCII proportionnelle"""
            filled = round((percent / 100) * 10) # Barre sur 10 caractères
            return "█" * filled + "░" * (10 - filled)

        for categorie in ["gratuit", "payant"]:
            total_cat = action_stats[categorie]["total"]
            if total_cat > 0:
                icone = "🟢" if categorie == "gratuit" else "🟠"
                reponse += f"{icone} <b>UTILISATION {categorie.upper()}</b>\n"
                
                # Tri des actions de la plus gourmande à la moins gourmande
                actions_triees = sorted(action_stats[categorie]["actions"].items(), key=lambda x: x[1], reverse=True)
                
                for fonction, tokens in actions_triees:
                    pourcentage = (tokens / total_cat) * 100
                    barre = format_bar(pourcentage)
                    
                    reponse += f"  • {fonction} : <b>{pourcentage:.1f}%</b>\n"
                    # La balise code permet un rendu typographique aligné (monospace) sur Telegram
                    reponse += f"    <code>{barre}</code>\n"
                reponse += "\n"
        
        await update.message.reply_text(reponse, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Erreur dans la commande /finance : {e}", exc_info=True)
        await update.message.reply_text("⚠️ Erreur technique lors de la récupération des données financières.")

async def main() -> None:
    """
    Fonction principale asynchrone orchestrant l'initialisation et le lancement des pipelines.
    """
    logger.info("=== DÉMARRAGE DU COPILOTE IA PERDIR ===")
    
    try:
        # 1. Chargement de la configuration stricte
        settings = get_settings()

        # 2. Initialisation et enregistrement des Services (Singletons via Dependency Injection)
        logger.info("Initialisation des services externes...")
        
        # - Service ChromaDB (Vectoriel Local)
        chroma_dir = os.path.abspath(settings.CHROMA_PERSIST_DIR)
        os.makedirs(chroma_dir, exist_ok=True)
        chroma_service = ChromaDBService(persist_directory=chroma_dir, embedding_model_name=settings.EMBEDDING_MODEL_NAME)
        set_chroma_service(chroma_service)
        
        # - Service Google Drive (OAuth)
        drive_service = GoogleDriveService(credentials_path=settings.GOOGLE_CREDENTIALS_PATH, token_path=settings.GOOGLE_TOKEN_PATH)
        await drive_service.authenticate()
        set_drive_service(drive_service)

        # - Service IMAP (Messagerie Académique)
        imap_service = IMAPService(host=settings.IMAP_HOST, user=settings.IMAP_USER, password=settings.IMAP_PASSWORD, port=settings.IMAP_PORT)
        await imap_service.connect()
        set_imap_service(imap_service)

        # - Service Telegram Bot
        telegram_service = TelegramBotService(token=settings.TELEGRAM_BOT_TOKEN, allowed_user_id=settings.TELEGRAM_ALLOWED_USER_ID)
        set_telegram_service(telegram_service)

        # - Service Token Tracker (Base de données SQLite locale)
        token_tracker = TokenTrackerService()
        set_token_tracker_service(token_tracker)

        # - Service Gemini Router (Gestionnaire de requêtes vers les modèles Gemini)
        gemini_router = GeminiRouterService()
        set_gemini_router_service(gemini_router)

        logger.info("Tous les services sont connectés et enregistrés.")

        # 3. Initialisation des Agents IA (Modèles Gemini)
        logger.info("Initialisation des cerveaux IA...")
        triage_agent = TriageAgent()
        orchestrator_agent = OrchestratorAgent()
        synth_agent = SynthAgent()

        # 4. Instanciation des Pipelines
        logger.info("Câblage des Pipelines d'exécution...")
        
        # - Pipeline A (Passif - Triage Automatique des Mails)
        pipeline_a = PipelineAMails(
            imap_service=imap_service,
            triage_agent=triage_agent,
            chroma_service=chroma_service,
            telegram_service=telegram_service
        )

        # - Pipeline B (Actif - Assistant Interactif Telegram)
        pipeline_b = PipelineBTelegram(
            telegram_service=telegram_service,
            orchestrator_agent=orchestrator_agent
        )

        # Enregistrement de la commande /finance pour le Perdir
        telegram_service.register_command("finance", finance_command)

        # Raccordement du gestionnaire de messages naturels Telegram vers le Pipeline B
        telegram_service.register_message_handler(pipeline_b.process_telegram_message)

        # - Pipeline C (Différé - Synthèse Stratégique)
        pipeline_c = PipelineCSynthesis(
            drive_service=drive_service,
            telegram_service=telegram_service,
            imap_service=imap_service,
            synth_agent=synth_agent,
            memoire_file_id=settings.MEMOIRE_FILE_ID,
            pipeline_b=pipeline_b
        )

        # 5. Démarrage des tâches asynchrones parallèles
        logger.info("🚀 Lancement des boucles de traitement asynchrones...")
        
        # Le rassemblement des tâches dans asyncio.gather assure le fonctionnement en concurrence 100% Async
        await asyncio.gather(
            telegram_service.start_polling(),                       # Écoute Telegram en Long Polling
            run_pipeline_a_loop(pipeline_a, interval_seconds=180),  # Relève des mails toutes les 3 minutes
            run_pipeline_c_loop(pipeline_c, target_hour=18)         # Synthèse programmée à partir de 18h
        )

    except KeyboardInterrupt:
        logger.info("Arrêt manuel de l'application demandé.")
    except Exception as e:
        logger.critical(f"Défaillance critique ayant entraîné l'arrêt du programme : {e}", exc_info=True)
    finally:
        # Nettoyage et fermeture propre des connexions persistantes à l'arrêt
        logger.info("Fermeture propre des services...")
        try:
            imap_to_close = get_imap_service()
            await imap_to_close.disconnect()
        except Exception:
            pass
        logger.info("Arrêt complet du Copilote.")


if __name__ == "__main__":
    # Lancement de l'Event Loop primaire
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programme terminé par l'utilisateur.")