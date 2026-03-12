"""Chat routes — Bob: assistant conversation (ADR-008)."""

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel
from typing import List, Literal

from app.presentation.routes.auth_routes import get_current_user
from app.agents.llm_client import llm_client
from app.config import settings

router = APIRouter(prefix="/api/v1/chat")

SYSTEM_PROMPT = """You are Bob, the AI assistant for Croo Digital Experience — an agent-first CRM.
You help users navigate the platform, automate tasks, and get insights using natural language.
Keep answers concise and actionable. You can suggest: viewing organizations, contacts, opportunities, quotes, activities; creating or searching entities; or summarizing data.
If the user asks something outside CRM scope, politely steer back to how you can help with their sales pipeline or data."""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a message to Bob and get a reply (conversation history in request)."""
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="Chat is not configured. Set GROQ_API_KEY in the environment.",
        )
    if not body.messages:
        raise HTTPException(status_code=400, detail="At least one message is required.")

    # Build messages for Groq: system + history (last N to avoid token limit)
    max_history = 20
    history = body.messages[-max_history:] if len(body.messages) > max_history else body.messages
    prompt = history[-1].content if history else ""
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Last message cannot be empty.")

    # For multi-turn we'd pass prior messages; Groq API accepts full messages list
    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[:-1]:
        messages_for_llm.append({"role": m.role, "content": m.content})
    messages_for_llm.append({"role": "user", "content": prompt})

    try:
        response = llm_client.client.chat.completions.create(
            model=llm_client.default_model,
            messages=messages_for_llm,
            temperature=0.3,
            max_tokens=1024,
        )
        reply = (response.choices[0].message.content or "").strip()
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Assistant unavailable: {str(e)}")
