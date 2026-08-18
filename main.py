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
    OrchestratorAgent
)
from src.workflows import (
    PipelineAMails,
    PipelineBTelegram,
)

from telegram import Update
from telegram.ext import ContextTypes

# Configuration initiale du logging avec rotation de fichier (max 5 Mo) pour le Raspberry Pi
LOG_FILE = Path("data/logs/copilote.log")
setup_logger(log_file_path=LOG_FILE, log_level=logging.INFO)
logger = get_logger("MainApp")

async def run_pipeline_a_loop(pipeline_a: PipelineAMails, interval_seconds: int = 300) -> None:
    """
    Boucle infinie pour exécuter le Pipeline A (Triage des Mails et Indexation) à intervalles réguliers (si mode POLLING sélectionné).
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


async def run_pipeline_a_idle_loop(pipeline_a: PipelineAMails) -> None:
    """
    Boucle infinie pour exécuter le Pipeline A en mode écoute permanente (si mode IDLE sélectionné).
    """
    logger.info("Démarrage de la tâche de fond : Pipeline A (Mode IDLE / Écoute permanente).")
    
    last_sent_index_time = datetime.now()

    # --- SYNCHRONISATION DE DÉMARRAGE ---
    logger.info("Synchronisation initiale : recherche des e-mails arrivés pendant que le Copilote était éteint...")
    try:
        # On utilise le Worker pour faire une relève classique avant de s'endormir
        await pipeline_a.run_pipeline(folder="INBOX", limit=50)
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation de démarrage : {e}")
    # ----------------------------------------------------
    
    while True:
        try:
            # 1. Écoute permanente. La fonction bloque ici jusqu'à un mouvement ou un timeout de 14min.
            await pipeline_a.run_pipeline_idle_mode(folder="INBOX", limit=50)
            
            # 2. SÉCURITÉ : La parade anti-retardataires
            # On force une relève classique silencieuse (Polling) au cas où un e-mail 
            # serait arrivé pile pendant que l'IA travaillait sur la rafale précédente.
            logger.debug("Vérification silencieuse des éventuels e-mails retardataires...")
            await pipeline_a.run_pipeline(folder="INBOX", limit=50)
            
            # 3. Indexation silencieuse des e-mails envoyés (toutes les ~15 minutes)
            # Puisque le timeout IDLE est de 14 min, cette condition s'activera naturellement à chaque réveil.
            now = datetime.now()
            if (now - last_sent_index_time).total_seconds() > 800:
                logger.debug("Indexation périodique des e-mails envoyés...")
                await pipeline_a.index_sent_emails(folder="Sent", limit=50)
                last_sent_index_time = now
                
        except asyncio.CancelledError:
            logger.info("Arrêt de la boucle IDLE du Pipeline A.")
            break
        except Exception as e:
            logger.error(f"Erreur inattendue dans la boucle IDLE du Pipeline A : {e}", exc_info=True)
            # Pause de sécurité de 60s en cas de crash réseau sévère pour ne pas spammer le serveur
            await asyncio.sleep(60)


async def finance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Commande Telegram /finance pour afficher la consommation visuelle du mois en cours."""
    logger.info("Commande /finance demandée par le Perdir.")
    try:
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
            
        total_cost_paid = 0.0
        total_cost_free = 0.0
        
        for modele, data in stats_mois.items():
            in_t, out_t = data['input'], data['output']
            
            # 1. Calcul du coût de base selon le type de modèle (Lite, Flash ou Pro)
            if "pro" in modele.lower():
                cost = (in_t * settings.PRICE_PRO_INPUT / 1000000) + (out_t * settings.PRICE_PRO_OUTPUT / 1000000)
            elif "lite" in modele.lower():
                cost = (in_t * settings.PRICE_FLASH_LITE_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_LITE_OUTPUT / 1000000)
            else:
                cost = (in_t * settings.PRICE_FLASH_INPUT / 1000000) + (out_t * settings.PRICE_FLASH_OUTPUT / 1000000)
                
            # 2. Répartition dans la bonne cagnotte (Gratuite ou Payante)
            if "gratuit" in modele.lower():
                total_cost_free += cost
            else:
                total_cost_paid += cost
            
        # --- Traduction manuelle du mois ---
        MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                   "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        mois_texte = MOIS_FR[now.month - 1]
        
        reponse = f"📊 <b>BILAN FINANCIER ({mois_texte} {now.year})</b>\n\n"
        reponse += f"💰 <b>Coût réel (Payant) : ~{total_cost_paid:.3f} $</b>\n"
        budget_restant = 10.0 - total_cost_paid
        reponse += f"🏦 <b>Budget Google restant : ~{budget_restant:.3f} $</b>\n\n"
        reponse += f"🎁 <b>Économies (Gratuit) : ~{total_cost_free:.3f} $</b>\n"
        reponse += f"<i>(Ce que vous auriez payé sans la clé gratuite)</i>\n\n"

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


async def synthese_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Déclenchée par /synthese.
    Demande directement à l'Orchestrateur de préparer la synthèse sans polluer l'historique.
    """
    logger.info("Commande /synthese déclenchée par l'utilisateur.")
    
    # On affiche "Le bot tape..." pour montrer que c'est pris en compte
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        # On récupère le Pipeline B depuis notre registre
        from src.core.dependencies import get_pipeline_b
        pipeline_b = get_pipeline_b()
        
        # Le "chuchotement" : C'est CE texte précis que l'Orchestrateur va lire et analyser !
        hidden_prompt = "Prépare la synthèse de la semaine. Pour cela, utilise exclusivement ton outil `generer_brouillon_synthese_hebdo`."
        
        # On parle directement au cerveau de l'IA (l'Orchestrateur)
        reponse = await pipeline_b.orchestrator_agent.process_user_request(
            user_message=hidden_prompt,
            chat_history=pipeline_b.chat_history
        )
        
        # On renvoie la réponse au Perdir (le lien du Google Doc généré par l'outil)
        await update.message.reply_text(reponse, parse_mode="HTML", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Erreur lors de la commande /synthese : {e}", exc_info=True)
        await update.message.reply_text("⚠️ Erreur technique lors de la création du brouillon.")


async def run_auto_synthesis_loop(telegram_service: TelegramBotService, pipeline_b: PipelineBTelegram) -> None:
    """
    Boucle de fond surveillant le jour et l'heure pour déclencher 
    la création automatique du brouillon de synthèse hebdomadaire.
    """
    settings = get_settings()
    logger.info(f"Démarrage de la tâche de fond : Synthèse Auto (Jour {settings.AUTO_SYNTHESIS_DAY}, {settings.AUTO_SYNTHESIS_HOUR}h00).")
    
    # On mémorise la date du dernier lancement pour ne pas le faire 50 fois le même jour
    last_run_date = None

    while True:
        try:
            now = datetime.now()
            
            # Vérification : Est-ce le bon jour (ex: 4=Vendredi) ET la bonne heure (ex: >= 18h) ?
            if now.weekday() == settings.AUTO_SYNTHESIS_DAY and now.hour >= settings.AUTO_SYNTHESIS_HOUR:
                
                # Vérification : Ne l'a-t-on pas déjà fait aujourd'hui ?
                if last_run_date != now.date():
                    logger.info("⏰ Condition de synthèse hebdomadaire remplie. Déclenchement automatique.")
                    
                    # Le "chuchotement" système
                    hidden_prompt = "Prépare la synthèse de la semaine. Pour cela, utilise exclusivement ton outil `generer_brouillon_synthese_hebdo`."
                    
                    # On fait travailler l'Orchestrateur
                    reponse = await pipeline_b.orchestrator_agent.process_user_request(
                        user_message=hidden_prompt,
                        chat_history=pipeline_b.chat_history
                    )
                    
                    # On envoie le message PROACTIVEMENT au Perdir sur Telegram
                    await telegram_service.send_notification(
                        message=f"🔔 <b>Synthèse Hebdomadaire Automatique</b>\n\n{reponse}",
                        disable_web_page_preview=True
                    )
                    
                    # On valide que c'est fait pour aujourd'hui
                    last_run_date = now.date()
                    logger.info("Synthèse automatique envoyée avec succès sur Telegram.")

        except asyncio.CancelledError:
            logger.info("Arrêt de la boucle de synthèse automatique.")
            break
        except Exception as e:
            logger.error(f"Erreur dans la boucle de synthèse automatique : {e}", exc_info=True)
        
        # Le système s'endort et vérifie l'heure toutes les 5 minutes
        await asyncio.sleep(300)

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

        from src.core.dependencies import set_pipeline_b
        set_pipeline_b(pipeline_b)

        # Enregistrement de la commande /finance pour le Perdir
        telegram_service.register_command("finance", finance_command)

        # Enregistrement de la commande /synthese pour le Perdir
        telegram_service.register_command("synthese", synthese_command)

        # Raccordement du gestionnaire de messages naturels Telegram vers le Pipeline B
        telegram_service.register_message_handler(pipeline_b.process_telegram_message)


        # 5. Démarrage des tâches asynchrones parallèles
        logger.info("🚀 Lancement des boucles de traitement asynchrones...")
        
        # --- L'AIGUILLAGE (Le commutateur Polling vs IDLE) ---
        if settings.IMAP_MODE.lower() == "idle":
            logger.info("Mode IMAP sélectionné : IDLE (Écoute permanente)")
            pipeline_a_task = run_pipeline_a_idle_loop(pipeline_a)
        else:
            logger.info("Mode IMAP sélectionné : POLLING (Relève par intervalle)")
            pipeline_a_task = run_pipeline_a_loop(pipeline_a, interval_seconds=180)

        # --- Préparation de la tâche de synthèse automatique ---
        auto_synth_task = run_auto_synthesis_loop(telegram_service, pipeline_b)

        # Le rassemblement des tâches dans asyncio.gather assure le fonctionnement en concurrence 100% Async
        await asyncio.gather(
            telegram_service.start_polling(),               # Écoute Telegram en Long Polling
            pipeline_a_task,                                # Relève des mails (Polling OU IDLE)
            auto_synth_task                                 # Synthèse automatique programmée
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
        os._exit(0)


if __name__ == "__main__":
    # Lancement de l'Event Loop primaire
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programme terminé par l'utilisateur.")