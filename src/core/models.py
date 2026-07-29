from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# --- Énumérations ---

class RouteChoice(str, Enum):
    AGENDA = "agenda"
    RAG_SEARCH = "rag_search"
    BRIEFING = "briefing"
    MAIN_COURANTE = "main_courante"
    STRATEGIC_BUFFER = "strategic_buffer"
    AUCUN_OU_INCOMPLET = "aucun_ou_incomplet"

class TypeActionAgenda(str, Enum):
    TASK = "tâche_google_tasks"
    CALENDAR = "événement_google_calendar"

# --- Modèles principaux (Objets circulant entre les modules) ---

class MailObject(BaseModel):
    """Représentation standardisée d'un e-mail entrant, prête pour l'indexation vectorielle."""
    id_mail: str = Field(..., description="Identifiant unique de l'e-mail provenant d'IMAP")
    date_reception: datetime = Field(..., description="Métadonnée : Date et heure de réception")
    expediteur: str = Field(..., description="Métadonnée : Adresse e-mail de l'expéditeur")
    sujet: str = Field(..., description="Métadonnée : Objet du mail")
    contenu_texte: str = Field(..., description="Corps du message servant à générer les embeddings")
    pieces_jointes: List[str] = Field(default_factory=list, description="Noms des pièces jointes")
    est_traite: bool = Field(default=False, description="Indique si le mail a déjà été traité par le workflow")
    nombre_tokens: Optional[int] = Field(None, description="Taille estimée du texte pour sécuriser l'envoi vers l'API d'embeddings")


class IA_TriResponse(BaseModel):
    """
    Objet DTO (Data Transfer Object) généré par le TriageAgent (Structured Output).
    Pilote les 4 actions automatiques du Pipeline A.
    L'IA ne manipule pas les IDs techniques.
    """
    dossier_cible: str = Field(
        ..., 
        description="Nom du dossier physique IMAP de destination"
    )
    necessite_notification: bool = Field(
        ..., 
        description="Vrai si l'e-mail nécessite une alerte Telegram immédiate au chef d'établissement (urgence critique)"
    )
    necessite_main_courante: bool = Field(
        ..., 
        description="Vrai si l'e-mail relate un incident (violence, conflit, accident) nécessitant une traçabilité officielle"
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

class IA_RouterResponse(BaseModel):
    """Objet DTO généré par le RouterAgent."""
    routes_choisies: List[RouteChoice] = Field(
        ..., 
        description="Liste des routes métiers détectées. Peut contenir plusieurs routes si le message exprime plusieurs demandes."
    )
    explication: Optional[str] = Field(
        None, 
        description="Si la route 'aucun_ou_incomplet' est choisie, explique brièvement pourquoi (ex: 'Il manque la date pour l'agenda', 'Message inaudible')."
    )

class AgendaTaskRequest(BaseModel):
    """Requête extraite par l'IA pour interagir avec Google Tasks ou Calendar."""
    type_action: TypeActionAgenda = Field(..., description="Création d'une tâche ou d'un lien d'agenda")
    titre: str = Field(..., description="Titre de la tâche ou de l'événement")
    date_cible: Optional[datetime] = Field(None, description="Date et heure cibles si détectées")
    description: Optional[str] = Field(None, description="Notes ou détails supplémentaires")