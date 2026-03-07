"""Bob Chat Agent — conversational CRM assistant powered by Qwen3 32B.

Manages chat sessions with conversation history and CRM-aware system prompt.
Uses the existing LLMClient wrapper with model override for Qwen3.
"""

import json
import re
import time
from typing import Optional
from threading import Lock

import structlog
from groq import Groq

from app.agents.llm_client import llm_client
from app.config import settings

logger = structlog.get_logger(__name__)

BOB_SYSTEM_PROMPT = """You are Bob, an intelligent CRM assistant for Croo Digital Experience.
You help users manage their contacts, organizations, opportunities, quotes, and activities.

Your capabilities:
- Answer questions about CRM data and best practices
- Help users create and manage contacts and organizations
- Provide insights about sales pipelines and opportunities
- Assist with workflow automation and task management
- Offer suggestions for follow-ups and engagement strategies

Communication style:
- Professional but friendly
- Concise and actionable — prefer short answers
- Use bullet points for lists
- When you can help with a specific action, offer to do it
- If you don't know something, say so honestly

Language: Respond in the same language as the user's message.
If the user speaks French, respond in French. If English, respond in English.

Context: You are integrated into a CRM platform. Users interact with you via a chat panel.

/no_think"""

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class ChatSession:
    """A single user's chat session with Bob."""

    def __init__(self, user_id: str, tenant_id: str, user_email: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.user_email = user_email
        self.messages: list[dict[str, str]] = []
        self.created_at = time.time()
        self.last_activity = time.time()
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.turn_count = 0

    def add_user_message(self, text: str) -> None:
        """Add a user message to the session history."""
        self.messages.append({"role": "user", "content": text})
        self.last_activity = time.time()

    def add_assistant_message(self, text: str) -> None:
        """Add Bob's response to the session history."""
        self.messages.append({"role": "assistant", "content": text})
        self.turn_count += 1

    def get_history_for_prompt(self) -> str:
        """Build conversation history string for the LLM prompt.

        Keeps only the last N messages to stay within context limits.
        """
        max_history = settings.bob_max_history
        recent = self.messages[-max_history:]

        parts = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Bob"
            parts.append(f"{role}: {msg['content']}")

        return "\n".join(parts)

    def is_expired(self) -> bool:
        """Check if session has exceeded TTL."""
        ttl_seconds = settings.bob_session_ttl_minutes * 60
        return (time.time() - self.last_activity) > ttl_seconds


class BobChatAgent:
    """Manages Bob chat sessions and generates responses via Groq."""

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}
        self._lock = Lock()

    def get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        tenant_id: str,
        user_email: str,
    ) -> ChatSession:
        """Get existing session or create a new one."""
        with self._lock:
            # Cleanup expired sessions
            self._cleanup_expired()

            if session_id not in self._sessions:
                self._sessions[session_id] = ChatSession(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    user_email=user_email,
                )
                logger.info(
                    "bob_session_created",
                    session_id=session_id,
                    user=user_email,
                )

            return self._sessions[session_id]

    # ── CRM action tools (same as voice pipeline) ───────
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "navigate_to",
                "description": "Navigate the user to a page in the CRM application.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "string",
                            "enum": [
                                "dashboard", "organizations", "contacts",
                                "opportunities", "quotes", "activities",
                                "settings", "knowledge-base",
                            ],
                            "description": "The page to navigate to.",
                        },
                    },
                    "required": ["page"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "open_create_dialog",
                "description": "Navigate to an entity list page and open the create/add new item dialog. If the user mentions a name, pass it so the search can be pre-filled.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity": {
                            "type": "string",
                            "enum": [
                                "organization", "contact", "opportunity",
                                "quote", "activity",
                            ],
                            "description": "The entity type to create.",
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional name/company name mentioned by the user to pre-fill the search field.",
                        },
                    },
                    "required": ["entity"],
                },
            },
        },
    ]

    def chat(
        self,
        session_id: str,
        user_message: str,
    ) -> tuple[str, list[dict]]:
        """Send a message to Bob and get a response + optional actions.

        Args:
            session_id: Session identifier
            user_message: The user's message text

        Returns:
            Tuple of (response_text, actions_list)
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.add_user_message(user_message)

        # Build system prompt with user's personality settings
        personality_directives = ""
        llm_temperature = settings.bob_temperature
        try:
            from app.infrastructure.database import SessionLocal
            from app.domain.entities.bob_settings import BobUserSettings
            db = SessionLocal()
            try:
                user_settings = BobUserSettings.get_or_create(db, session.user_id)
                tone_map = {
                    "professional": "Professional but friendly",
                    "friendly": "Warm, friendly and approachable",
                    "casual": "Casual and relaxed, like chatting with a colleague",
                    "formal": "Formal and polished",
                }
                length_map = {
                    "concise": "Keep responses very concise — short sentences, bullet points.",
                    "balanced": "Keep responses balanced — concise but informative.",
                    "detailed": "Give thorough, detailed responses when helpful.",
                }
                lang_map = {
                    "auto": "Respond in the same language as the user's message.",
                    "en": "Always respond in English.",
                    "fr": "Always respond in French (Français).",
                    "es": "Always respond in Spanish (Español).",
                    "de": "Always respond in German (Deutsch).",
                }
                tone_desc = tone_map.get(user_settings.tone, "Professional but friendly")
                length_desc = length_map.get(user_settings.response_length, "Keep responses balanced.")
                lang_desc = lang_map.get(user_settings.language, "Respond in the same language as the user's message.")
                emoji_note = " You may use emoji when appropriate." if user_settings.emoji_usage else ""

                personality_directives = f"""
Personality (from user preferences):
- Communication style: {tone_desc}
- {length_desc}
- {lang_desc}{emoji_note}
"""
                # Map creativity (0-1) to temperature (0.1-1.0)
                llm_temperature = max(0.1, min(1.0, user_settings.creativity))
            finally:
                db.close()
        except Exception as e:
            logger.warning("bob_settings_lookup_failed", error=str(e))

        system_prompt = BOB_SYSTEM_PROMPT + personality_directives
        messages = [{"role": "system", "content": system_prompt}]
        max_history = settings.bob_max_history
        messages.extend(session.messages[-max_history:])

        try:
            client = Groq(api_key=settings.groq_api_key)

            response = client.chat.completions.create(
                model=settings.bob_model,
                messages=messages,
                tools=self.TOOLS,
                tool_choice="auto",
                temperature=llm_temperature,
                max_tokens=2048,
            )

            choice = response.choices[0]
            actions: list[dict] = []

            # Handle tool calls
            if choice.message.tool_calls:
                # Process each tool call
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    fn = tc.function.name

                    if fn == "navigate_to":
                        actions.append({
                            "type": "navigate",
                            "page": args.get("page", "dashboard"),
                        })
                    elif fn == "open_create_dialog":
                        entity = args.get("entity", "contact")
                        name = args.get("name")
                        page_map = {
                            "organization": "organizations",
                            "contact": "contacts",
                            "opportunity": "opportunities",
                            "quote": "quotes",
                            "activity": "activities",
                        }
                        action_dict: dict = {
                            "type": "open_create_dialog",
                            "entity": entity,
                            "page": page_map.get(entity, "contacts"),
                        }
                        if name:
                            action_dict["name"] = name
                        actions.append(action_dict)

                    logger.info(
                        "bob_tool_call",
                        session_id=session_id,
                        function=fn,
                        arguments=args,
                    )

                # Add tool call + result to context, then get follow-up
                # Build a clean assistant message (model_dump() includes
                # unsupported fields like executed_tools that Groq rejects)
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.message.tool_calls
                    ],
                }
                messages.append(assistant_msg)
                for tc in choice.message.tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": '{"status": "ok"}',
                    })

                # Get the follow-up text response
                followup = client.chat.completions.create(
                    model=settings.bob_model,
                    messages=messages,
                    temperature=settings.bob_temperature,
                    max_tokens=512,
                )
                response_text = followup.choices[0].message.content or ""
            else:
                response_text = choice.message.content or ""

            # Strip <think>...</think> blocks
            response_text = _THINK_RE.sub("", response_text).strip()

            session.add_assistant_message(response_text)

            logger.info(
                "bob_chat_response",
                session_id=session_id,
                user=session.user_email,
                turn=session.turn_count,
                actions=len(actions),
            )

            return response_text, actions

        except Exception as e:
            logger.error(
                "bob_chat_error",
                session_id=session_id,
                error=str(e),
            )
            raise

    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info("bob_session_deleted", session_id=session_id)
                return True
            return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get session metadata."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "user_email": session.user_email,
            "turn_count": session.turn_count,
            "created_at": session.created_at,
            "last_activity": session.last_activity,
            "message_count": len(session.messages),
        }

    def list_sessions(self, user_id: str) -> list[dict]:
        """List all active sessions for a user."""
        with self._lock:
            self._cleanup_expired()
            return [
                self.get_session_info(sid)
                for sid, s in self._sessions.items()
                if s.user_id == user_id
            ]

    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired()
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.info("bob_session_expired", session_id=sid)


# Singleton
bob_agent = BobChatAgent()
