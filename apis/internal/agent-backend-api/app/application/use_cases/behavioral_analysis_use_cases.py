"""Behavioral analysis use cases owned by the internal Agent Backend."""

from typing import Any, Protocol

from app.application.use_cases.client_map_use_cases import ClientMapRepositoryPort
from app.domain.exceptions import ContactNotFoundError


class BehavioralProfileProviderPort(Protocol):
    async def analyze(self, signals: dict[str, Any]) -> dict[str, Any]:
        ...


class BehavioralAnalysisUseCases:
    def __init__(
        self,
        repo: ClientMapRepositoryPort,
        provider: BehavioralProfileProviderPort,
    ) -> None:
        self.repo = repo
        self.provider = provider

    async def analyze(self, contact_id: str, user: dict[str, Any]) -> dict[str, Any]:
        tenant_id = user["tenant_id"]
        if not self.repo.contact_exists(contact_id, tenant_id):
            raise ContactNotFoundError

        client_map = self.repo.get_by_contact_id(contact_id, tenant_id)
        if not client_map:
            client_map = self.repo.upsert(
                contact_id=contact_id,
                tenant_id=tenant_id,
                data={},
                user_email=user.get("email") or "",
            )

        profile = await self.provider.analyze(self._build_signals(client_map))
        self.repo.upsert(
            contact_id=contact_id,
            tenant_id=tenant_id,
            data={"behavioral_profile": profile},
            user_email=user.get("email") or "",
        )
        return profile

    def _build_signals(self, client_map: Any) -> dict[str, Any]:
        golden_notes = list(getattr(client_map, "golden_notes", []) or [])
        signals: dict[str, Any] = {
            "golden_note_signals": {},
            "client_map_context": {
                "role_type": getattr(client_map, "role_type", None),
                "disc_profile": getattr(client_map, "disc_profile", None),
                "company_culture": getattr(client_map, "company_culture", None),
                "pain_point": getattr(client_map, "pain_point", None),
                "ego_driver": getattr(client_map, "ego_driver", None),
                "trust_level": getattr(client_map, "trust_level", None),
                "meddpicc_score": getattr(client_map, "meddpicc_score", None),
            },
        }
        if golden_notes:
            signals["golden_note_signals"] = {
                "total_notes": len(golden_notes),
                "emotional_sequence": [
                    getattr(note, "emotional_climate", "NEUTRAL") or "NEUTRAL"
                    for note in golden_notes[:10]
                ],
                "interaction_type_distribution": [
                    str(getattr(note, "interaction_type", "UNKNOWN") or "UNKNOWN")
                    for note in golden_notes[:10]
                ],
                "sample_verbatims": [
                    getattr(note, "verbatim", None)
                    for note in golden_notes
                    if getattr(note, "verbatim", None)
                ][:3],
            }
        return signals
