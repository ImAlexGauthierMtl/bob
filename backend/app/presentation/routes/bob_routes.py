"""Bob chat routes — REST API for Bob conversational agent.

Endpoints for sending messages to Bob, managing chat sessions,
and retrieving conversation history.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

import structlog

from app.presentation.routes.auth_routes import get_current_user
from app.agents.bob_chat_agent import bob_agent
from app.middleware.rate_limiter import rate_limiter

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/bob")


# ── Schemas ──────────────────────────────────────

class ChatRequest(BaseModel):
    """Request to send a message to Bob."""
    message: str
    session_id: Optional[str] = None


class BobAction(BaseModel):
    """An action Bob wants the UI to perform."""
    type: str          # 'navigate' | 'open_create_dialog'
    page: Optional[str] = None
    entity: Optional[str] = None
    name: Optional[str] = None


class ChatResponse(BaseModel):
    """Bob's response to a chat message."""
    response: str
    session_id: str
    turn_count: int
    actions: list[BobAction] = []


class SessionInfo(BaseModel):
    """Session metadata."""
    session_id: str
    user_id: str
    user_email: str
    turn_count: int
    created_at: float
    last_activity: float
    message_count: int


# ── Routes ───────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def bob_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a message to Bob and receive a response.

    If no session_id is provided, a new session will be created.
    """
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    # Rate limit check
    rate_limiter.check_chat(current_user["user_id"])

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = bob_agent.get_or_create_session(
        session_id=session_id,
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        user_email=current_user["email"],
    )

    try:
        response_text, actions = bob_agent.chat(
            session_id=session_id,
            user_message=request.message,
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            turn_count=session.turn_count,
            actions=[BobAction(**a) for a in actions],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error("bob_chat_route_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bob encountered an error. Please try again.",
        )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
):
    """List all active Bob chat sessions for the current user."""
    sessions = bob_agent.list_sessions(current_user["user_id"])
    return sessions


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Close and delete a Bob chat session."""
    # Verify the session belongs to this user
    info = bob_agent.get_session_info(session_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if info["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's session",
        )

    bob_agent.delete_session(session_id)
