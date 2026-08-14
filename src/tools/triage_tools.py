import json
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.utils import get_logger

logger = get_logger(__name__)

# Emplacement du fichier de mémoire des consignes
FICHIER_CONSIGNES = Path("data/consignes_triage.json")

# Verrou asynchrone pour éviter la corruption du fichier JSON si 
# l'Orchestrateur (Pipeline B) et le Triage (Pipeline A) y accèdent en même temps
_consignes_lock = asyncio.Lock()

def _charger_consignes_sync() -> list:
    """Charge les consignes depuis le fichier JSON (Logique bloquante isolée)."""
    if not FICHIER_CONSIGNES.exists():
        return []
    try:
        with open(FICHIER_CONSIGNES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur de lecture du fichier des consignes de triage : {e}")
        return []

def _sauvegarder_consignes_sync(consignes: list) -> None:
    """Sauvegarde les consignes dans le fichier JSON (Logique bloquante isolée)."""
    FICHIER_CONSIGNES.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(FICHIER_CONSIGNES, "w", encoding="utf-8") as f:
            json.dump(consignes, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erreur d'écriture du fichier des consignes de triage : {e}")


async def gerer_consignes_triage(action: str, id_consigne: Optional[str] = None, condition: Optional[str] = None, action_exigee: Optional[str] = None) -> str:
    """
    Outil permettant à l'IA d'ajouter, de lister ou de supprimer des consignes temporaires 
    de surveillance et de triage des e-mails.
    
    RÈGLES STRICTES POUR L'AJOUT DE CONSIGNE :
    1. L'argument `condition` doit être rédigé en langage naturel, de manière large et sémantique (ex: "un mail provenant du maire ou de la mairie", "un message parlant de la cantine"). Évite d'utiliser des adresses e-mail exactes ou des objets stricts, car c'est une autre IA (l'Agent de Triage) qui lira cette condition et elle doit pouvoir comprendre l'intention même si l'adresse de l'expéditeur varie.
    2. L'argument `action_exigee` doit décrire explicitement le traitement attendu. Il peut porter sur :
       - UNIQUEMENT le classement (ex: "Classer dans le dossier 'A traiter'"). L'Agent de Triage décidera seul de l'alerte.
       - UNIQUEMENT l'alerte (ex: "Déclencher une alerte Telegram"). L'Agent de Triage décidera seul du dossier de classement.
       - LES DEUX (ex: "Classer dans 'Inbox' et déclencher une alerte Telegram").

    RÈGLE STRICTE POUR LA SUPPRESSION :
    Si l'utilisateur demande d'arrêter une surveillance (supprimer), tu NE PEUX PAS deviner l'identifiant (`id_consigne`). Tu DOIS obligatoirement procéder en deux étapes :
    1. Appeler une première fois cet outil avec l'action "lister" pour récupérer la liste des consignes actives et lire leurs IDs.
    2. Appeler une seconde fois cet outil avec l'action "supprimer" en utilisant l'ID exact que tu viens d'obtenir.

    Args:
        action (str): L'action à effectuer ("ajouter", "lister", "supprimer").
        id_consigne (Optional[str]): L'identifiant de la consigne (requis pour "supprimer").
        condition (Optional[str]): La description sémantique du mail à surveiller (requis pour "ajouter").
        action_exigee (Optional[str]): Ce que le trieur doit faire (requis pour "ajouter").
        
    Returns:
        str: Le résultat de l'opération en langage naturel.
    """
    logger.info(f"Outil 'gerer_consignes_triage' appelé avec l'action : {action}")
    
    async with _consignes_lock:
        # On utilise to_thread pour ne jamais bloquer l'Event Loop principal
        consignes = await asyncio.to_thread(_charger_consignes_sync)
        
        if action == "ajouter":
            if not condition or not action_exigee:
                return "Erreur : 'condition' et 'action_exigee' sont obligatoires pour ajouter une consigne."
            
            if not consignes:
                nouvel_id = "C1"
            else:
                try:
                    # On cherche le plus grand nombre derrière le "C" et on fait +1
                    max_id = max(int(c["id_consigne"].replace("C", "")) for c in consignes)
                    nouvel_id = f"C{max_id + 1}"
                except ValueError:
                    # Fallback de sécurité si un ID a été corrompu manuellement
                    nouvel_id = f"C{len(consignes) + 1}"
            
            nouvelle_consigne = {
                "id_consigne": nouvel_id,
                "condition": condition,
                "action_exigee": action_exigee,
                "date_ajout": datetime.now().strftime("%d/%m/%Y à %H:%M")
            }
            consignes.append(nouvelle_consigne)
            
            await asyncio.to_thread(_sauvegarder_consignes_sync, consignes)
            return f"Succès : La consigne de surveillance a été ajoutée sous l'ID {nouvel_id}."
            
        elif action == "lister":
            if not consignes:
                return "Il n'y a actuellement aucune consigne de triage temporaire active."
            
            result = "Voici les consignes actives actuellement respectées par l'agent de triage :\n"
            for c in consignes:
                result += f"- [ID: {c['id_consigne']}] Si '{c['condition']}' -> ALORS '{c['action_exigee']}'\n"
            return result
            
        elif action == "supprimer":
            if not id_consigne:
                return "Erreur : 'id_consigne' est obligatoire pour supprimer une consigne."
            
            consignes_filtrees = [c for c in consignes if c["id_consigne"] != id_consigne]
            if len(consignes_filtrees) == len(consignes):
                return f"Erreur : Aucune consigne trouvée avec l'ID {id_consigne}."
                
            await asyncio.to_thread(_sauvegarder_consignes_sync, consignes_filtrees)
            return f"Succès : La consigne {id_consigne} a été désactivée et supprimée de la mémoire."
            
        else:
            return "Erreur : Action non reconnue. Utilisez 'ajouter', 'lister' ou 'supprimer'."