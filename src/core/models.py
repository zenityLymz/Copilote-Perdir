from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# --- Énumérations ---

class DossierCible(str, Enum):
    INBOX = "Inbox"
    A_TRAITER = "A traiter"
    NON_URGENT = "Non urgent"
    LECTURE = "Lecture"
    TRASH = "Trash"


class TypeActionAgenda(str, Enum):
    TASK = "tâche_google_tasks"
    CALENDAR = "événement_google_calendar"

# --- Modèles principaux (Objets circulant entre les modules) ---

class MailObject(BaseModel):
    """Représentation standardisée d'un e-mail entrant, prête pour l'indexation vectorielle."""
    id_mail: str = Field(..., description="Identifiant unique de l'e-mail provenant d'IMAP")
    date_reception: datetime = Field(..., description="Métadonnée : Date et heure de réception")
    expediteur: str = Field(..., description="Métadonnée : Adresse e-mail de l'expéditeur")
    destinataires: Optional[str] = Field(None, description="Métadonnée : Adresses e-mail des destinataires principaux (To)")
    copies: Optional[str] = Field(None, description="Métadonnée : Adresses e-mail en copie (Cc)")
    sujet: str = Field(..., description="Métadonnée : Objet du mail")
    contenu_texte: str = Field(..., description="Corps du message servant à générer les embeddings")
    pieces_jointes: List[str] = Field(default_factory=list, description="Noms des pièces jointes")
    est_traite: bool = Field(default=False, description="Indique si le mail a déjà été traité par le workflow")
    nombre_tokens: Optional[int] = Field(None, description="Taille estimée du texte pour sécuriser l'envoi vers l'API d'embeddings")
    dossier_source: Optional[str] = Field(None, description="Dossier IMAP d'origine (utile pour le marquage)")


class IA_TriResponse(BaseModel):
    """
    Objet DTO (Data Transfer Object) généré par le TriageAgent (Structured Output).
    Pilote les actions automatiques du Pipeline A.
    L'IA ne manipule pas les IDs techniques.
    """
    dossier_cible: DossierCible = Field(
        ..., 
        description="Nom du dossier physique IMAP de destination"
    )
    necessite_notification: bool = Field(
        ..., 
        description="Vrai si l'e-mail nécessite une alerte Telegram immédiate au chef d'établissement (urgence critique)"
    )
    justification: str = Field(
        ..., 
        description="Brève explication (1 ou 2 phrases maximum) de la décision de triage"
    )

class TriDecision(IA_TriResponse):
    """
    L'objet métier complet circulant dans le Pipeline A.
    Il combine l'intelligence de l'IA (héritage) et le contexte technique (id_mail).
    """
    id_mail: str = Field(..., description="Identifiant unique de l'e-mail provenant d'IMAP")


class AgendaTaskRequest(BaseModel):
    """Requête extraite par l'IA pour interagir avec Google Tasks ou Calendar."""
    type_action: TypeActionAgenda = Field(..., description="Création d'une tâche ou d'un lien d'agenda")
    titre: str = Field(..., description="Titre de la tâche ou de l'événement")
    date_cible: Optional[datetime] = Field(None, description="Date et heure cibles si détectées")
    description: Optional[str] = Field(None, description="Notes ou détails supplémentaires")


class ConversationTurn(BaseModel):
    """
    Représente un tour de parole unique dans l'historique conversationnel.
    """
    role: str = Field(
        ..., 
        description="Le rôle de l'émetteur du message (généralement 'user', 'model' ou 'system')."
    )
    message: str = Field(
        ..., 
        description="Le contenu textuel du message."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, 
        description="Horodatage exact du message"
    )
    est_synthetise: bool = Field(
        default=False, 
        description="Indique si le message a déjà été traité par la synthèse de la mémoire de l'établissement."
    )

class ChatHistory(BaseModel):
    """
    Représente l'historique complet d'une conversation avec l'Agent Orchestrateur.
    Permet à l'IA de conserver le contexte à court terme.
    """
    turns: List[ConversationTurn] = Field(
        default_factory=list, 
        description="Liste chronologique des échanges entre l'utilisateur et l'IA."
    )