"""Training data access."""
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.training_models import TrainingMissingElement, TrainingNote, TrainingSession


class TrainingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, session: TrainingSession) -> TrainingSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: str, user_id: str) -> Optional[TrainingSession]:
        return self.db.query(TrainingSession).filter(
            TrainingSession.id == session_id,
            TrainingSession.user_id == user_id,
        ).first()

    def update_session_slide(self, session: TrainingSession, current_slide: int) -> None:
        session.current_slide = current_slide
        self.db.commit()

    def list_notes(self, session_id: str, user_id: str) -> list[TrainingNote]:
        return self.db.query(TrainingNote).filter(
            TrainingNote.session_id == session_id,
            TrainingNote.user_id == user_id,
        ).order_by(TrainingNote.created_at.asc()).all()

    def create_note(self, note: TrainingNote) -> TrainingNote:
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_note(self, note_id: str, user_id: str) -> Optional[TrainingNote]:
        return self.db.query(TrainingNote).filter(
            TrainingNote.id == note_id,
            TrainingNote.user_id == user_id,
        ).first()

    def delete_note(self, note: TrainingNote) -> None:
        self.db.delete(note)
        self.db.commit()

    def list_missing(self, session_id: str, user_id: str) -> list[TrainingMissingElement]:
        return self.db.query(TrainingMissingElement).filter(
            TrainingMissingElement.session_id == session_id,
            TrainingMissingElement.user_id == user_id,
        ).order_by(TrainingMissingElement.created_at.asc()).all()

    def create_missing(self, item: TrainingMissingElement) -> TrainingMissingElement:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_missing(self, item_id: str, user_id: str) -> Optional[TrainingMissingElement]:
        return self.db.query(TrainingMissingElement).filter(
            TrainingMissingElement.id == item_id,
            TrainingMissingElement.user_id == user_id,
        ).first()

    def delete_missing(self, item: TrainingMissingElement) -> None:
        self.db.delete(item)
        self.db.commit()
