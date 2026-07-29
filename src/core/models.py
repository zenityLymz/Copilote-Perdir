from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

# --- Énumérations ---

class NiveauPriorite(str, Enum):
    INFO = "info"
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"

class CategoriePilotage(str, Enum):
    BATI = "bâti"
    RH = "rh"
    FINANCES = "finances"
    CLIMAT = "climat"
    AUTRE = "autre"

class TypeMainCourante(str, Enum):
    NOMINATIF = "nominatif"
    EVENEMENTIEL = "événementiel"

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
    
    # Nouveaux champs pour la production
    est_traite: bool = Field(default=False, description="Indique si le mail a déjà été traité par le workflow")
    nombre_tokens: Optional[int] = Field(None, description="Taille estimée du texte pour sécuriser l'envoi vers l'API d'embeddings")

class IA_TriResponse(BaseModel):
    """
    Objet DTO (Data Transfer Object) représentant uniquement 
    la production intellectuelle attendue de l'IA.
    L'IA ne manipule pas les IDs techniques.
    """
    niveau_priorite: NiveauPriorite = Field(..., description="Niveau d'urgence évalué par l'IA")
    dossier_cible: str = Field(..., description="Nom du dossier physique IMAP de destination")
    justification: str = Field(..., description="Brève explication de la décision de l'IA")
    necessite_notification: bool = Field(..., description="Vrai si notification Telegram requise")

class TriDecision(IA_TriResponse):
    """
    L'objet métier complet circulant dans l'application.
    Il combine l'intelligence de l'IA (héritage) et le contexte technique (id_mail).
    """
    id_mail: str = Field(..., description="Identifiant unique de l'e-mail provenant d'IMAP")


class EventLog(BaseModel):
    """Entrée pour la main courante (traçabilité d'événements sensibles)."""
    type_log: TypeMainCourante = Field(..., description="S'agit-il d'un suivi de personne ou d'un événement global ?")
    cible_document: str = Field(..., description="Nom de l'élève, du personnel ou de l'événement pour cibler le bon Google Doc")
    date_evenement: datetime = Field(default_factory=datetime.now, description="Incrémentation chronologique")
    description_factuelle: str = Field(..., description="Description neutre et factuelle des faits")
    actions_prises: Optional[str] = Field(None, description="Actions immédiates réalisées par le chef d'établissement")
    
    # Nouveau champ pour la traçabilité
    source_id: Optional[str] = Field(None, description="ID du mail source ayant déclenché l'entrée dans la main courante")

class PilotageInfo(BaseModel):
    """Élément d'information stratégique pour le fichier de pilotage ultra-synthétique."""
    date_extraction: datetime = Field(default_factory=datetime.now)
    categorie: CategoriePilotage = Field(..., description="Thématique de l'information (Bâti, RH, Finances, Climat)")
    synthese_info: str = Field(..., description="Synthèse de l'information structurelle ou macro")
    source_id: Optional[str] = Field(None, description="ID du mail source extrait de manière autonome par l'IA")

class AgendaTaskRequest(BaseModel):
    """Requête extraite par l'IA pour interagir avec Google Tasks ou Calendar."""
    type_action: TypeActionAgenda = Field(..., description="Création d'une tâche ou d'un lien d'agenda")
    titre: str = Field(..., description="Titre de la tâche ou de l'événement")
    date_cible: Optional[datetime] = Field(None, description="Date et heure cibles si détectées")
    description: Optional[str] = Field(None, description="Notes ou détails supplémentaires")
    
    # Nouveau champ pour la traçabilité
    source_id: Optional[str] = Field(None, description="ID du mail source justifiant la tâche ou le RDV")