"""Bob Chat v1 facade routes."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.application.use_cases.bob_chat_use_cases import BobChatUseCases
from app.domain import DEFAULT_CHANNEL, BobChatError
from app.domain.entities import BobChatMessageCommand, BobChatMission
from app.presentation.deps import get_bob_chat_use_cases


router = APIRouter()


class BobChatMissionPayload(BaseModel):
    id: Optional[str] = None
    prompt: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)


class BobChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    session_id: Optional[str] = None
    channel: str = DEFAULT_CHANNEL
    mission: Optional[BobChatMissionPayload] = None
    client_context: dict[str, Any] = Field(default_factory=dict)

    def to_command(self) -> BobChatMessageCommand:
        return BobChatMessageCommand(
            message=self.message,
            session_id=self.session_id,
            channel=self.channel,
            mission=(
                BobChatMission(
                    id=self.mission.id,
                    prompt=self.mission.prompt,
                    context=self.mission.context,
                )
                if self.mission
                else None
            ),
            client_context=self.client_context,
        )


@router.post("/messages")
async def create_message(
    body: BobChatMessageRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_cases: BobChatUseCases = Depends(get_bob_chat_use_cases),
) -> dict[str, Any]:
    try:
        return await use_cases.create_message(
            command=body.to_command(),
            idempotency_key=idempotency_key,
            forward_headers=request.headers,
            trace_id=_trace_id(request),
        )
    except BobChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/sessions")
async def list_sessions(
    request: Request,
    use_cases: BobChatUseCases = Depends(get_bob_chat_use_cases),
) -> dict[str, Any]:
    try:
        return await use_cases.list_sessions(
            forward_headers=request.headers,
            trace_id=_trace_id(request),
        )
    except BobChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    use_cases: BobChatUseCases = Depends(get_bob_chat_use_cases),
) -> dict[str, Any]:
    try:
        return await use_cases.get_session(
            session_id=session_id,
            forward_headers=request.headers,
            trace_id=_trace_id(request),
        )
    except BobChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    request: Request,
    use_cases: BobChatUseCases = Depends(get_bob_chat_use_cases),
) -> None:
    try:
        await use_cases.delete_session(
            session_id=session_id,
            forward_headers=request.headers,
            trace_id=_trace_id(request),
        )
    except BobChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _trace_id(request: Request) -> str:
    raw = request.headers.get("x-trace-id") or request.headers.get("x-request-id") or uuid4().hex
    normalized = "".join(character for character in raw.lower() if character.isalnum())
    return normalized[:32].ljust(32, "0")
