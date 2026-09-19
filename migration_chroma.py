import chromadb
from datetime import datetime
import logging

# Configuration des logs pour suivre l'opération en direct
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("Migration")

def migrer_dates_vers_timestamp():
    # 1. Connexion à la base vectorielle locale
    client = chromadb.PersistentClient(path="./data/chroma_db")
    
    # Remplacer par le nom exact de votre collection dans src/services/chroma_service.py
    NOM_COLLECTION = "emails" 
    
    try:
        collection = client.get_collection(name=NOM_COLLECTION)
        logger.info(f"Collection '{NOM_COLLECTION}' trouvée. Récupération de l'historique...")
    except Exception as e:
        logger.error(f"Impossible d'ouvrir la collection : {e}")
        return

    # 2. Extraction globale de la base
    donnees = collection.get()
    ids = donnees.get("ids", [])
    metadatas = donnees.get("metadatas", [])
    
    if not ids:
        logger.info("La base est vide, aucune migration nécessaire.")
        return

    logger.info(f"{len(ids)} e-mails trouvés. Début de l'analyse des métadonnées...")

    ids_a_maj = []
    metadatas_a_maj = []

    # 3. Boucle de conversion
    for i, meta in enumerate(metadatas):
        if meta and "date_reception" in meta:
            valeur_date = meta["date_reception"]
            
            # On vérifie si la donnée est au format texte (à corriger)
            if isinstance(valeur_date, str):
                try:
                    # Remplacement du "Z" éventuel pour la compatibilité Python
                    valeur_propre = valeur_date.replace("Z", "+00:00")
                    dt_obj = datetime.fromisoformat(valeur_propre)
                    
                    # Transformation mathématique en Timestamp Unix (entier)
                    meta["date_reception"] = int(dt_obj.timestamp())
                    
                    ids_a_maj.append(ids[i])
                    metadatas_a_maj.append(meta)
                    
                except ValueError as e:
                    logger.warning(f"Échec de conversion pour l'ID {ids[i]} ({valeur_date}): {e}")
            
            # Si isinstance(valeur_date, int) -> Le format est déjà bon, on l'ignore.

    # 4. Injection de masse (Batch update)
    if ids_a_maj:
        logger.info(f"Remplacement de {len(ids_a_maj)} dates en cours...")
        try:
            collection.update(ids=ids_a_maj, metadatas=metadatas_a_maj)
            logger.info("✅ Migration terminée avec succès ! La base parle désormais en Timestamp.")
        except Exception as e:
            logger.error(f"Erreur fatale lors de l'enregistrement : {e}")
    else:
        logger.info("✅ Aucune date textuelle détectée. L'historique est déjà au bon format.")

if __name__ == "__main__":
    migrer_dates_vers_timestamp()