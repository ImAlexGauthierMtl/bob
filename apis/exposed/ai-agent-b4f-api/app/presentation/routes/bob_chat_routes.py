"""Bob chat routes — text chat, session listing, session deletion.

Stub implementation: returns placeholder responses until LLM integration
is wired up.  Matches the frontend BobChatResponse / BobSessionInfo contracts.
"""

import uuid
import time
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user

router = APIRouter(prefix="/bob")


# ── Request / Response schemas ───────────────────────────────────────

class BobChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    mission_prompt: Optional[str] = None
    mission_context: Optional[Dict[str, Any]] = None
    channel: Optional[str] = None  # compact | workspace | voice_app | voice_phone


class BobChatAction(BaseModel):
    type: str
    page: Optional[str] = None
    entity: Optional[str] = None
    name: Optional[str] = None


class BobToolStep(BaseModel):
    tool: str
    status: str


class BobArtifactField(BaseModel):
    label: str
    value: str


class BobArtifact(BaseModel):
    type: str
    title: str
    fields: List[BobArtifactField] = []
    status: str = "complete"


class BobChatResponse(BaseModel):
    response: str
    session_id: str
    turn_count: int = 1
    actions: List[BobChatAction] = []
    tool_steps: Optional[List[BobToolStep]] = None
    artifact: Optional[BobArtifact] = None
    session_title: Optional[str] = None


class BobSessionInfo(BaseModel):
    session_id: str
    user_id: str
    user_email: str
    turn_count: int = 0
    created_at: float
    last_activity: float
    message_count: int = 0
    title: Optional[str] = None


# ── In-memory session store (temporary until persistence is added) ───

_sessions: Dict[str, dict] = {}


def _current_user_id(current_user: dict) -> str:
    return current_user.get("user_id") or current_user.get("sub", "")


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/chat", response_model=BobChatResponse)
async def bob_chat(body: BobChatRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """Process a chat message and return Bob's response.

    Currently returns a stub placeholder. Replace with LLM orchestration.
    """
    session_id = body.session_id or str(uuid.uuid4())
    now = time.time()

    # Upsert session in memory
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "user_id": _current_user_id(current_user),
            "user_email": current_user.get("email", ""),
            "turn_count": 0,
            "created_at": now,
            "last_activity": now,
            "message_count": 0,
            "title": None,
        }

    sess = _sessions[session_id]
    sess["turn_count"] += 1
    sess["message_count"] += 1
    sess["last_activity"] = now

    # Generate a title from the first message
    if sess["title"] is None:
        sess["title"] = body.message[:60] + ("…" if len(body.message) > 60 else "")

    # TODO: Replace with real LLM call
    stub_response = (
        "I'm Bob, your AI assistant. My chat capabilities are currently being set up. "
        "I'll be fully operational soon! In the meantime, feel free to explore the other features."
    )

    return BobChatResponse(
        response=stub_response,
        session_id=session_id,
        turn_count=sess["turn_count"],
        actions=[],
        session_title=sess["title"],
    )


@router.get("/sessions", response_model=List[BobSessionInfo])
async def list_sessions(request: Request, current_user: dict = Depends(get_current_user)):
    """List all chat sessions for the current user."""
    user_id = _current_user_id(current_user)
    user_sessions = [
        BobSessionInfo(**s)
        for s in _sessions.values()
        if s.get("user_id") == user_id
    ]
    # Sort by last_activity descending
    user_sessions.sort(key=lambda s: s.last_activity, reverse=True)
    return user_sessions


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Delete a chat session."""
    user_id = _current_user_id(current_user)
    sess = _sessions.get(session_id)
    if sess and sess.get("user_id") == user_id:
        del _sessions[session_id]
