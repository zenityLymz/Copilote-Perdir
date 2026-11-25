# CAHIER DES CHARGES : Copilote IA pour Personnel de Direction

## 1. Vision Globale et Objectif

Ce document définit l'architecture, les fonctionnalités et les règles d'ingénierie du projet **Copilote Perdir**. Il sert de référence technique pour toute évolution confiée à des développeurs ou des IA expertes.

Le système est un programme Python tournant 24h/24 et 7j/7 sur un **Raspberry Pi** (environnement Linux *headless*). Il agit comme un assistant virtuel proactif et autonome pour un Chef d'Établissement de l'Éducation Nationale (Perdir). Son cœur repose sur une **architecture orientée Agents (*Agentic Workflow*)** : un cerveau central (`OrchestratorAgent`), doté d'une mémoire conversationnelle persistante, raisonne sur les demandes, pose des questions si des paramètres manquent, et déclenche dynamiquement une boîte à outils (Mails, Drive, Agenda, Tâches) pour alléger la charge mentale quotidienne. En complément de l'interface conversationnelle naturelle, quelques commandes slash utilitaires (`/finance`, `/synthese`, `/drive`) permettent des actions techniques directes.

---

## 2. Architecture des Flux (Pipelines et Tâches de Fond)

Le système repose sur une architecture asynchrone orientée événements (`asyncio.gather` dans `main.py`), découpée en flux indépendants :

### Pipeline A : Traitement Automatique des E-mails (Passif)
Fonctionne en continu en tâche de fond pour filtrer, classer et mémoriser la messagerie académique (IMAP).
* **Déclencheur :** Mode **IMAP IDLE** (écoute permanente avec timeout de 4 min 30 et passe de rattrapage anti-retardataires) ou mode **POLLING** par intervalle, configurable dans `.env`.
* **Agent impliqué :** `TriageAgent` (Gemini `flash-lite`), enrichi dynamiquement par les consignes temporaires de surveillance (`data/consignes_triage.json`).
* **Actions orchestrées automatiquement :**
  * *Extraction :* Nettoyage HTML et extraction du texte des pièces jointes (PDF, DOCX, TXT) avant analyse.
  * *Alerte immédiate :* Notification Telegram en cas d'urgence critique détectée.
  * *Tri physique & Marquage :* Déplacement de l'e-mail dans le dossier cible (`Inbox`, `A traiter`, `Non urgent`, `Lecture`, `Cepages`, `Trash`) et pose du flag IMAP personnalisé **`CopiloteTraite`** (indépendant du statut lu/non lu par l'humain).
  * *Mémorisation RAG :* Indexation vectorielle locale dans ChromaDB (hors `Trash`).
  * *Indexation silencieuse des envois :* Relève périodique du dossier `Sent` pour indexer les e-mails envoyés par le Perdir dans ChromaDB sans solliciter d'agent IA.

### Pipeline B : L'Assistant Interactif Autonome (Actif)
Cœur conversationnel du Copilote, basé sur une boucle agentique (*Agentic Loop*).
* **Déclencheur :** Message texte ou mémo vocal envoyé sur Telegram. Les vocaux sont téléchargés et transcrits directement en **mémoire vive (RAM)** via Gemini (`flash-lite`), sans écriture sur le disque du Raspberry Pi.
* **Agent central :** `OrchestratorAgent` (Gemini `flash`). Interlocuteur unique du Perdir, il s'appuie sur l'historique conversationnel pour comprendre le contexte, demander des précisions si nécessaire, enchaîner les outils et formuler une réponse unifiée.

### Synthèse Hebdomadaire Automatique et Commandes Utilitaires
En complément des deux pipelines, `main.py` orchestre une tâche planifiée et trois commandes Telegram directes :
* **Synthèse hebdomadaire (`run_auto_synthesis_loop` & `/synthese`) :** Déclenchée automatiquement chaque semaine (configurable via `AUTO_SYNTHESIS_DAY` / `AUTO_SYNTHESIS_HOUR`) ou à la demande via `/synthese`. `SynthAgent` analyse uniquement les échanges Telegram non encore synthétisés, les compare à la structure du document maître « Mémoire de l'Établissement » (Google Doc), et génère un **brouillon Google Doc** (à partir de HTML) contenant des propositions de mise à jour pour validation humaine manuelle. Si rien n'est stratégique, aucun document n'est créé.
* **Suivi budgétaire (`/finance`) :** Interroge la base SQLite locale (`TokenTrackerService`) pour afficher le coût mensuel réel (clé payante), le budget restant, les économies réalisées (clé gratuite) et la répartition visuelle par fonction.
* **Synchronisation Cloud (`/drive`) :** Commande purement déterministe (sans IA) qui télécharge une archive ZIP depuis le cloud académique (Nextcloud), l'extrait temporairement sur le SSD, réplique l'arborescence sur Google Drive, puis nettoie les fichiers temporaires.

---

## 3. Le Cerveau IA : Orchestrateur, Sous-Agents et Mémoires

* **Interlocuteur unique (`OrchestratorAgent`) :** Seul composant autorisé à dialoguer avec le Perdir. Les sous-agents travaillent en arrière-plan et lui renvoient leurs résultats.
* **Mémoire conversationnelle :** Persistée localement dans `data/chat_history.json` avec une fenêtre glissante de **10 jours** (`CHAT_HISTORY_RETENTION_DAYS`). Chaque tour de parole est horodaté et porte un marqueur `est_synthetise` pour la synthèse hebdomadaire. Les prises de notes simples (« retiens que… ») ne déclenchent aucun outil et sont conservées naturellement dans cet historique.
* **Mémoire de l'établissement :** Document Google Docs maître (annuaire, rôles, contexte stratégique, habitudes de l'établissement), consulté à la demande via un outil dédié.
* **Sous-agents spécialisés et routage par paliers :** Chaque agent est rattaché à l'un des 3 paliers de modèles Gemini configurables dans `config.py` (`flash-lite`, `flash`, `pro`) :
  * `TriageAgent` (`flash-lite`) : Décision de triage en sortie JSON structurée (`IA_TriResponse`).
  * `BriefingAgent` (`flash-lite`) : Synthèse rapide des e-mails non lus pour lecture mobile.
  * `MainCouranteAgent` (`flash`) : Rédaction neutre, factuelle et juridique des incidents avec harmonisation des balises `@Role_Nom` et `#Evenement`.
  * `DraftAgent` (`flash`) : Rédaction de brouillons d'e-mails imitant le style du Perdir via une *Voice Card* locale (`data/style_perdir.md`).
  * `SynthAgent` (`flash`) : Propositions de mise à jour de la Mémoire de l'établissement en HTML.

---

## 4. La Boîte à Outils de l'IA (Function Calling)

L'Orchestrateur pilote ses actions exclusivement via des fonctions Python documentées (`src/tools/`) exposées au SDK natif `google-genai` :

### A. Gestion Documentaire et Incidents (Google Drive)
* `lire_memoire_etablissement()` : Lit le contenu texte brut du Google Doc maître pour contextualiser une demande.
* `rechercher_info_drive(mots_cles, annee_archive)` : Recherche plein texte dans le Drive avec exclusion automatique des archives des années scolaires passées (préfixes `RXX_` calculés depuis `ARCHIVE_START_YEAR`), sauf demande explicite d'archive.
* `preparer_brouillon_main_courante(texte_brut)` : Extrait les tags `@`/`#` existants de `Main_Courante.md` et fait rédiger un brouillon par `MainCouranteAgent` pour validation humaine obligatoire.
* `sauvegarder_main_courante_validee(texte_valide)` : Concatène et sauvegarde l'entrée validée dans `Main_Courante.md` (*Read-Rewrite-Replace*), uniquement après accord explicite du Perdir.
* `generer_brouillon_synthese_hebdo()` : Compile les tours de conversation non synthétisés, appelle `SynthAgent`, crée le Google Doc brouillon et acquitte les tours en RAM.
* `lister_dossiers_racine_drive()` : Liste l'arborescence cloisonnée du dossier du collège pour permettre à l'IA de choisir le dossier cible avant un transfert.

### B. Communication et Mails (IMAP & ChromaDB)
* `rechercher_dans_les_emails(requete_semantique, date_debut, date_fin, expediteur, annee_archive)` : Recherche sémantique (RAG) dans ChromaDB avec filtres de métadonnées (timestamps Unix, expéditeur) et montage à la volée des bases archivées (`data/chroma_db_YYYY-YYYY`).
* `generer_briefing_emails(criteres, limite)` : Scanne les dossiers IMAP (hors corbeille/spams/brouillons) pour relever les mails `UNSEEN` et génère un résumé via `BriefingAgent`.
* `enregistrer_brouillon_mail(destinataire, sujet, contexte_original, directives_de_redaction)` : Délègue la rédaction stylisée à `DraftAgent` et injecte le brouillon dans le dossier `Drafts` via IMAP `APPEND`.
* `transferer_pj_vers_drive(timestamp_mail, nom_piece_jointe, id_dossier_drive, nouveau_nom, ajouter_prefixe_annee)` : Extrait une pièce jointe depuis IMAP, la renomme (avec préfixe `RXX_` optionnel), l'uploade sur Drive et nettoie le dossier temporaire.
* `gerer_consignes_triage(action, id_consigne, condition, action_exigee)` : Ajoute, liste ou supprime des règles de surveillance temporaires dans `data/consignes_triage.json`.

### C. Organisation et Planification (Google Workspace & Telegram)
* `gerer_agenda(action, ...)` : Outil complet (*lire*, *creer*, *modifier*, *supprimer*) pour Google Calendar avec gestion des lieux et vérification préalable des disponibilités.
* `gerer_taches(action, ...)` : Outil complet (*lire*, *creer*, *modifier*, *valider*, *supprimer*) pour Google Tasks.
* `programmer_alerte(message_rappel, delai_minutes)` : Planifie un minuteur asynchrone renvoyant une notification Telegram à court terme.

---

## 5. Infrastructure et Services Techniques (Les Fondations)

Les agents et outils ne communiquent jamais directement avec l'extérieur : ils passent par la couche `src/services/`, dédiée aux connexions réseau, à l'authentification et aux I/O :

* **`TelegramBotService` :** Interface `python-telegram-bot` (v20+) en *Long Polling* asynchrone, filtrage strict par `TELEGRAM_ALLOWED_USER_ID`, envoi exclusif en HTML et découpage automatique des réponses dépassant 4 096 caractères.
* **`IMAPService` :** Double gestionnaire de connexion (Worker + Listener IDLE), reconnexion automatique (`_ensure_connected`), téléchargement par lots (*batch fetching*), extraction de pièces jointes et commande `APPEND`.
* **`GoogleDriveService` & `GoogleCalendarTasksService` :** Interactions avec Drive, Calendar et Tasks via OAuth 2.0, avec rafraîchissement automatique du token et protection anti-figeage en environnement *headless*.
* **`ChromaDBService` :** Base vectorielle locale persistante (`data/chroma_db`) utilisant `gemini-embedding-001` via un wrapper compatible `google-genai`.
* **`GeminiRouterService` :** Centralise tous les appels LLM. Gère deux clés API (`GEMINI_API_KEY_FREE` et `GEMINI_API_KEY_PAID`), applique le `force_paid` sur les tâches critiques, bascule automatiquement sur la clé payante en cas d'erreur `429`/`503`/`500`, et transmet la consommation au tracker.
* **`TokenTrackerService` :** Enregistre chaque appel Gemini (modèle, tokens in/out, contexte) dans une base SQLite locale (`data/token_usage.db`).
* **`AcademicCloudService` :** Télécharge en streaming les archives ZIP du cloud académique, les extrait sur SSD et garantit leur nettoyage.

---

## 6. Spécifications Techniques, Rigueur et Contraintes Logicielles

Tout développement ou refactoring doit respecter impérativement les standards suivants :

* **Python 3.11+ & Typage Strict :** Toutes les fonctions, méthodes et variables sont typées. Les données circulant entre modules sont validées par des modèles **Pydantic** (`src/core/models.py`) et la configuration par `pydantic-settings` (`src/core/config.py`).
* **100 % Asynchrone (`asyncio`) :** Aucune opération ne doit bloquer l'Event Loop. Tout appel synchrone ou bloquant (IMAP, I/O disque, SQLite, appels HTTP synchrones) doit être encapsulé dans `asyncio.to_thread()` et protégé par un `asyncio.Lock` si un accès concurrent est possible.
* **SDK Natif Google uniquement :** L'usage de frameworks lourds ou « boîtes noires » (LangChain, LlamaIndex, CrewAI, AutoGen…) est **strictement interdit**. Toutes les interactions LLM et le *Function Calling* utilisent exclusivement le SDK officiel `google-genai`.
* **Découplage et Séparation des Responsabilités :**
  * `src/core/` : Modèles Pydantic, configuration, registre de dépendances, hiérarchie d'exceptions (`AssistantPerdirError` et dérivées).
  * `src/services/` : Infrastructure pure (réseau, auth, I/O), aucune logique métier IA.
  * `src/agents/` & `src/prompts/` : Logique IA et prompts strictement séparés du reste du code.
  * `src/tools/` : Fonctions métier exposées à l'Orchestrateur.
  * `src/workflows/` : Orchestration des pipelines.
  * `src/utils/` : Utilitaires transverses (logging, nettoyage HTML, troncature intelligente par tokens, gestion des dates/archives).
* **Registre de Dépendances (*Service Locator*) :** Les services persistants sont enregistrés comme singletons dans `src/core/dependencies.py` et récupérés via leurs getters (`get_imap_service()`, `get_drive_service()`, etc.) afin d'éviter les imports circulaires et les reconnexions inutiles.
* **Programmation Défensive et Dégradation Gracieuse :**
  * Protection `try/except` systématique autour de tout appel réseau, I/O ou LLM : une panne externe ne doit **jamais** faire crasher le programme.
  * En cas d'échec d'un outil, retourner un message d'erreur clair à l'Orchestrateur pour qu'il informe poliment le Perdir.
  * Protection *headless* obligatoire sur tout flux OAuth (`os.name == 'posix' and 'DISPLAY' not in os.environ`).
  * Journalisation via `get_logger(__name__)` avec rotation de fichiers (`RotatingFileHandler`, max 5 Mo) pour préserver la carte SD/SSD du Raspberry Pi.
* **Interface Telegram en HTML strict :** Utilisation exclusive de `ParseMode.HTML` (`<b>`, `<i>`, `<u>`, `<pre>`). Le Markdown est proscrit dans les réponses Telegram pour éviter les erreurs de parsing ; les contenus externes (expéditeurs, sujets) sont échappés via `html.escape()`.

---

## 7. Évolution Architecturale à Venir : Migration Google Workspace MCP

Conformément aux nouvelles règles d'accès Google Workspace pour les agents IA (application technique au **1er février 2027**), la couche d'accès à **Google Drive, Google Calendar et Google Tasks** devra être migrée prochainement des API REST classiques vers les **serveurs MCP (*Model Context Protocol*) officiels de Google Workspace**.

Cette migration suivra strictement le principe de découplage du projet :
* **Conservation de la façade métier :** `OrchestratorAgent` et `src/tools/` restent inchangés (les serveurs MCP ne sont pas branchés directement sur le LLM afin de préserver les garde-fous Python et éviter toute explosion des tokens d'entrée).
* **Remplacement de la couche transport :** seule la couche `src/services/` évoluera pour s'appuyer sur un client MCP asynchrone dédié, avec un client OAuth 2.0 spécifique « agent IA » séparé de l'accès REST conservé pour la commande non-IA `/drive`.