"""Repository for Client Map 360° — CRUD + MEDDPICC score calculation."""

import structlog
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.domain.entities.client_map import ClientMap, GoldenNote
from app.domain.entities.base import generate_uuid

logger = structlog.get_logger(__name__)


# ── MEDDPICC Weight Configuration ────────────────────────────
# Each letter maps to fields that compose the score.
# Total possible = 100 points.

MEDDPICC_COMPONENTS = {
    "M": {
        "label": "Metrics",
        "max": 14,
        "fields": ["metrics_target", "wiifm_business"],
    },
    "E": {
        "label": "Economic Buyer",
        "max": 14,
        "fields": ["economic_buyer"],
    },
    "D1": {
        "label": "Decision Criteria",
        "max": 12,
        "fields": ["decision_criteria"],
    },
    "D2": {
        "label": "Decision Process",
        "max": 12,
        "fields": ["decision_process", "paper_process"],
    },
    "P": {
        "label": "Paper Process",
        "max": 8,
        "fields": ["paper_process"],
    },
    "I": {
        "label": "Identified Pain",
        "max": 14,
        "fields": ["pain_point", "pain_business_impact", "pain_personal_impact"],
    },
    "C1": {
        "label": "Champion",
        "max": 14,
        "fields": ["champion_name"],
    },
    "C2": {
        "label": "Competition",
        "max": 12,
        "fields": ["competition", "alternative_if_no"],
    },
}


def compute_meddpicc_score(client_map: ClientMap) -> tuple[int, dict]:
    """Compute MEDDPICC score from field completeness.

    Returns:
        Tuple of (total_score, component_breakdown)
    """
    total = 0
    breakdown = {}

    for key, cfg in MEDDPICC_COMPONENTS.items():
        filled = sum(1 for f in cfg["fields"] if getattr(client_map, f, None))
        possible = len(cfg["fields"])
        score = round(cfg["max"] * (filled / possible)) if possible else 0
        total += score
        breakdown[key] = {
            "label": cfg["label"],
            "score": score,
            "max": cfg["max"],
            "filled_fields": filled,
            "total_fields": possible,
        }

    return min(total, 100), breakdown


class ClientMapRepository:
    """Data access for ClientMap + GoldenNote."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_contact_id(self, contact_id: str, tenant_id: str) -> Optional[ClientMap]:
        """Get client map by contact_id with eager-loaded children."""
        return (
            self.db.query(ClientMap)
            .options(
                joinedload(ClientMap.golden_notes),
                joinedload(ClientMap.insight_triples),
            )
            .filter(
                ClientMap.contact_id == contact_id,
                ClientMap.tenant_id == tenant_id,
                ClientMap.is_deleted == False,
            )
            .first()
        )

    def upsert(self, contact_id: str, tenant_id: str, data: dict, user_email: str = "") -> ClientMap:
        """Create or update a client map, auto-computing MEDDPICC score."""
        existing = (
            self.db.query(ClientMap)
            .filter(
                ClientMap.contact_id == contact_id,
                ClientMap.tenant_id == tenant_id,
            )
            .first()
        )

        if existing:
            # Update only non-None fields
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            client_map = existing
        else:
            client_map = ClientMap(
                id=generate_uuid(),
                contact_id=contact_id,
                tenant_id=tenant_id,
                created_by=user_email,
                **{k: v for k, v in data.items() if v is not None},
            )
            self.db.add(client_map)

        # Auto-compute MEDDPICC score
        score, _ = compute_meddpicc_score(client_map)
        client_map.meddpicc_score = score

        self.db.commit()
        self.db.refresh(client_map)

        logger.info(
            "client_map_upserted",
            contact_id=contact_id,
            meddpicc_score=score,
            is_new=existing is None,
        )
        return client_map

    # ── Golden Notes ─────────────────────────────────────────

    def add_golden_note(
        self,
        client_map_id: str,
        tenant_id: str,
        data: dict,
        user_email: str = "",
    ) -> GoldenNote:
        """Create a new golden note and attach to client map."""
        note = GoldenNote(
            id=generate_uuid(),
            client_map_id=client_map_id,
            tenant_id=tenant_id,
            created_by=user_email,
            **data,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)

        logger.info(
            "golden_note_created",
            note_id=note.id,
            client_map_id=client_map_id,
            interaction_type=data.get("interaction_type"),
        )
        return note

    def update_golden_note(self, note_id: str, tenant_id: str, data: dict) -> Optional[GoldenNote]:
        """Update an existing golden note."""
        note = (
            self.db.query(GoldenNote)
            .filter(
                GoldenNote.id == note_id,
                GoldenNote.tenant_id == tenant_id,
                GoldenNote.is_deleted == False,
            )
            .first()
        )
        if not note:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(note, key, value)
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_golden_note(self, note_id: str, tenant_id: str) -> bool:
        """Soft-delete a golden note."""
        note = (
            self.db.query(GoldenNote)
            .filter(
                GoldenNote.id == note_id,
                GoldenNote.tenant_id == tenant_id,
            )
            .first()
        )
        if not note:
            return False
        note.is_deleted = True
        self.db.commit()
        return True

    def get_meddpicc_detail(self, contact_id: str, tenant_id: str) -> Optional[dict]:
        """Get detailed MEDDPICC score breakdown."""
        client_map = self.get_by_contact_id(contact_id, tenant_id)
        if not client_map:
            return None
        score, breakdown = compute_meddpicc_score(client_map)
        return {
            "total_score": score,
            "max_score": 100,
            "components": breakdown,
        }
