# Règles du projet — Copilote Perdir

## 1. Architecture & Référence
- **Avant toute modification architecturale**, consulter obligatoirement `cahier_des_charges_copilote_perdir.md` à la racine du projet et s'y conformer.

## 2. Contraintes techniques strictes
- **Python 3.11+ typé** : annoter systématiquement les paramètres et valeurs de retour (type hints).
- **100 % asynchrone (`asyncio`)** : ne jamais bloquer l'event loop ; isoler toute opération synchrone/bloquante via `asyncio.to_thread` et protéger les accès concurrents (`asyncio.Lock`) si nécessaire.
- **SDK natif `google-genai` uniquement** : ne jamais introduire LangChain ni aucun framework d'orchestration IA tiers.
- **Codage défensif** :
  - Encadrer les appels externes et opérations critiques par des blocs `try/except` explicites (sans faire crasher les boucles principales).
  - Utiliser `get_logger` (`src.utils.logger`) pour toute journalisation.
  - Conserver systématiquement la **protection headless** (détection `os.name == "posix" and "DISPLAY" not in os.environ` avant tout flux OAuth navigateur, afin de ne jamais figer le Raspberry Pi).

## 3. Protocole de travail obligatoire
- **Un seul fichier modifié à la fois.**
- **Jamais de génération ou de modification en masse.**
- **Attendre la validation explicite de l'utilisateur** après chaque modification avant de passer à l'étape ou au fichier suivant.
