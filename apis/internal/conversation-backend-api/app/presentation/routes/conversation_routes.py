"""Internal conversation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.application.use_cases.conversation_use_cases import ConversationUseCases
from app.domain import ConversationError, ConversationNotFoundError, InternalContext
from app.presentation.deps import get_conversation_use_cases, get_internal_context
from app.presentation.schemas.conversation_schemas import (
    MessageCreateRequest,
    MessageListResponse,
    MessageResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
)


router = APIRouter(prefix="/internal/conversation/v1")


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreateRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> SessionResponse:
    session = await use_cases.create_session(
        context=context,
        title=body.title,
        channel=body.channel,
        mission=body.mission,
        client_context=body.client_context,
    )
    return SessionResponse.from_domain(session)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> SessionListResponse:
    sessions = await use_cases.list_sessions(context=context)
    return SessionListResponse(items=[SessionResponse.from_domain(item) for item in sessions])


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> SessionResponse:
    try:
        session = await use_cases.get_session(context=context, session_id=session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return SessionResponse.from_domain(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> None:
    try:
        await use_cases.delete_session(context=context, session_id=session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    session_id: str,
    body: MessageCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> MessageResponse:
    try:
        message = await use_cases.add_message(
            context=context,
            session_id=session_id,
            role=body.role,
            content=body.content,
            metadata=body.metadata,
            idempotency_key=idempotency_key,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except ConversationError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return MessageResponse.from_domain(message)


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: ConversationUseCases = Depends(get_conversation_use_cases),
) -> MessageListResponse:
    try:
        messages = await use_cases.list_messages(context=context, session_id=session_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return MessageListResponse(items=[MessageResponse.from_domain(item) for item in messages])
