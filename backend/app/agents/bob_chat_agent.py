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
- CRITICAL: If the user asks for their training (e.g. "ma formation CRM", "start training") or complains the presentation isn't showing ("ne montre pas la présentation", "I don't see the presentation"), you MUST immediately call the `start_crm_training` tool. Do NOT just say "I don't see it". Let the tool do the navigation.

UI Controls & Chained Actions:
- When the user asks to change the text in a search/create dialog, use `ui_update_input`. Set submit=true if they want to execute the search immediately.
- When the user says "choose number X", "select the second one", use `ui_select_result` with the requested index.
- You can CHAIN actions: if the user says "create organization Shopify, choose the first result, then create contact Tobi", you must generate multiple tool calls in sequence if possible, or accomplish them step by step. Do your best to guide them through the UI fluently.

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

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        user_email: str,
        mission_prompt: Optional[str] = None,
        mission_context: Optional[dict] = None,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.user_email = user_email
        self.mission_prompt = mission_prompt
        self.mission_context = mission_context or {}
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
        mission_prompt: Optional[str] = None,
        mission_context: Optional[dict] = None,
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
                    mission_prompt=mission_prompt,
                    mission_context=mission_context,
                )
                logger.info(
                    "bob_session_created",
                    session_id=session_id,
                    user=user_email,
                    has_mission=mission_prompt is not None,
                )

            return self._sessions[session_id]

    # Removed local TOOLS list; imported dynamically in chat()

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

        # ── Inject mission prompt if active ──────────
        if session.mission_prompt:
            system_prompt += f"\n\n{session.mission_prompt}"
            logger.info(
                "mission_prompt_injected",
                session_id=session_id,
                prompt_length=len(session.mission_prompt),
            )

        messages = [{"role": "system", "content": system_prompt}]
        max_history = settings.bob_max_history
        messages.extend(session.messages[-max_history:])

        # ── Nudge tool calls when mission is active ──────
        if session.mission_prompt and session.turn_count > 1:
            messages.append({
                "role": "system",
                "content": (
                    "RAPPEL IMPÉRATIF: Tu DOIS appeler bcc_update_profile à CHAQUE réponse "
                    "pour sauvegarder les insights extraits de la conversation. "
                    "D'abord appelle l'outil, PUIS donne ta réponse avec ta prochaine question. "
                    "N'oublie pas: entity_type=organization, perspective=ceo. "
                    "Sections disponibles: vision, mission, culture, competition, description, brand_dna."
                ),
            })

        # ── Setup tools: UI actions + CRM data operations
        from app.agents.bob_tools import BOB_TOOLS
        active_tools = BOB_TOOLS

        try:
            client = Groq(api_key=settings.groq_api_key)

            response = client.chat.completions.create(
                model=settings.bob_model,
                messages=messages,
                tools=active_tools,
                tool_choice="auto",
                temperature=llm_temperature,
                max_tokens=2048,
            )

            choice = response.choices[0]
            actions: list[dict] = []

            # ── Debug: trace LLM tool behavior ──────────
            finish_reason = choice.finish_reason
            tool_calls = choice.message.tool_calls
            logger.info(
                "bob_llm_response",
                session_id=session_id,
                finish_reason=finish_reason,
                has_tool_calls=bool(tool_calls),
                tool_count=len(tool_calls) if tool_calls else 0,
                tool_names=[tc.function.name for tc in tool_calls] if tool_calls else [],
                has_mission=bool(session.mission_prompt),
                content_preview=(choice.message.content or "")[:100],
            )

            # Handle tool calls
            if choice.message.tool_calls:
                # Process each tool call
                tool_results: dict[str, str] = {}
                for tc in choice.message.tool_calls:
                    args = json.loads(tc.function.arguments)
                    fn = tc.function.name

                    if fn == "navigate_to":
                        actions.append({
                            "type": "navigate",
                            "page": args.get("page", "dashboard"),
                        })
                        tool_results[tc.id] = '{"status": "ok"}'
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
                        tool_results[tc.id] = '{"status": "ok"}'
                    elif fn == "start_crm_training":
                        actions.append({
                            "type": "navigate",
                            "page": "template/crm-mastery",
                        })
                        tool_results[tc.id] = '{"status": "ok"}'
                    elif fn == "search_and_open_entity":
                        import concurrent.futures
                        import asyncio
                        from app.agents.tool_executor import execute_bob_tool
                        from app.infrastructure.database import SessionLocal

                        def _run_open_entity():
                            db = SessionLocal()
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                user_ctx = {
                                    "user_id": session.user_id,
                                    "tenant_id": session.tenant_id,
                                    "session_id": session_id,
                                }
                                res = loop.run_until_complete(
                                    execute_bob_tool("search_and_open_entity", args, user_ctx, db)
                                )
                                loop.close()
                                return res
                            finally:
                                db.close()

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(_run_open_entity)
                            search_res = future.result(timeout=10)
                            
                        if search_res and search_res.get("status") == "ok":
                            actions.append({
                                "type": "navigate",
                                "page": search_res.get("page")
                            })
                            tool_results[tc.id] = json.dumps({"status": "ok", "message": search_res.get("message")})
                        else:
                            tool_results[tc.id] = json.dumps({"status": "error", "message": search_res.get("message", "Not found.")})
                            
                    elif fn == "change_training_slide":
                        action_dict = {
                            "type": "change_slide",
                            "direction": args.get("direction", "next"),
                        }
                        slide_num = args.get("slide_number")
                        if slide_num is not None:
                            action_dict["slide_number"] = slide_num
                        actions.append(action_dict)
                        tool_results[tc.id] = '{"status": "ok"}'
                    elif fn == "ui_update_input":
                        actions.append({
                            "type": "ui_update_input",
                            "text": args.get("text", ""),
                            "submit": args.get("submit", False)
                        })
                        tool_results[tc.id] = '{"status": "ok"}'
                    elif fn == "ui_select_result":
                        actions.append({
                            "type": "ui_select_result",
                            "index": args.get("index", 1)
                        })
                        tool_results[tc.id] = '{"status": "ok"}'
                    elif fn == "ui_switch_tab":
                        actions.append({
                            "type": "ui_switch_tab",
                            "page": args.get("tab_name", ""),
                        })
                        tool_results[tc.id] = '{"status": "ok"}'
                    else:
                        # Execute BCC / CRM tools via tool_executor
                        # Must run in a separate thread since we're inside
                        # FastAPI's async event loop
                        import concurrent.futures
                        import asyncio
                        from app.agents.tool_executor import execute_bob_tool
                        from app.infrastructure.database import SessionLocal

                        def _run_tool():
                            db = SessionLocal()
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                user_context = {
                                    "user_id": session.user_id,
                                    "tenant_id": session.tenant_id,
                                    "session_id": session_id,
                                }
                                result = loop.run_until_complete(
                                    execute_bob_tool(fn, args, user_context, db)
                                )
                                loop.close()
                                return json.dumps(result)
                            finally:
                                db.close()

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(_run_tool)
                            tool_results[tc.id] = future.result(timeout=30)

                    logger.info(
                        "bob_tool_call",
                        session_id=session_id,
                        function=fn,
                        arguments=args,
                    )

                # Add tool call + result to context, then get follow-up
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
                        "content": tool_results.get(tc.id, '{"status": "ok"}'),
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

            # ── Post-response: extract & save insights for mission ──
            if session.mission_prompt and session.turn_count >= 3:
                try:
                    self._extract_and_save_insights(
                        client=client,
                        session=session,
                        session_id=session_id,
                    )
                except Exception as ex:
                    logger.warning("insight_extraction_failed", error=str(ex))

            return response_text, actions

        except Exception as e:
            logger.error(
                "bob_chat_error",
                session_id=session_id,
                error=str(e),
            )
            raise

    def _extract_and_save_insights(
        self,
        client,
        session: "ChatSession",
        session_id: str,
    ) -> None:
        """Extract structured insights from conversation and save to BCC."""
        import re

        # Extract entity_id from mission prompt
        entity_id_match = re.search(
            r"entity_id[=:]\s*([a-f0-9-]{36})",
            session.mission_prompt or "",
        )
        if not entity_id_match:
            logger.warning("insight_extraction_no_entity_id", session_id=session_id)
            return

        entity_id = entity_id_match.group(1)

        # Get last 4 messages for context
        recent = session.messages[-4:]
        conversation_text = "\n".join(
            f"{'CEO' if m['role'] == 'user' else 'Bob'}: {m['content']}"
            for m in recent if m.get("content")
        )

        extraction_prompt = f"""Analyse cette conversation d'interview CEO et extrais les insights.

CONVERSATION RÉCENTE:
{conversation_text}

INSTRUCTIONS:
- Extrais UNIQUEMENT les informations que le CEO a réellement partagées
- Retourne un JSON VALIDE avec les sections remplies
- Si une section n'a pas d'info dans cette conversation, mets null
- Sois concis mais capturer l'essentiel

Retourne SEULEMENT ce JSON, rien d'autre:
{{
  "vision": "texte ou null",
  "mission": "texte ou null",
  "culture": "texte ou null",
  "competition": "texte ou null",
  "description": "texte ou null",
  "brand_dna": "texte ou null"
}}"""

        try:
            extraction = client.chat.completions.create(
                model=settings.bob_model,
                messages=[
                    {"role": "system", "content": "Tu es un extracteur de données JSON. Retourne UNIQUEMENT du JSON valide, sans texte autour, sans commentaire, sans balise markdown."},
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
            )

            raw = extraction.choices[0].message.content or ""
            # Strip think tags, markdown, and find JSON object
            raw = _THINK_RE.sub("", raw).strip()
            # Extract JSON between first { and last }
            start_idx = raw.find("{")
            end_idx = raw.rfind("}")
            if start_idx == -1 or end_idx == -1:
                logger.warning("insight_extraction_no_json", raw_preview=raw[:200])
                return
            raw = raw[start_idx:end_idx + 1]

            insights = json.loads(raw)

            # Save each non-null insight using ThreadPoolExecutor
            # (we're inside FastAPI's async loop)
            from app.infrastructure.database import SessionLocal
            from app.agents.bob_tools import execute_tool
            import asyncio
            import concurrent.futures

            def _save_insight(section_name: str, section_content: str):
                db = SessionLocal()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        execute_tool(
                            "bcc_update_profile",
                            {
                                "entity_type": "organization",
                                "entity_id": entity_id,
                                "section": section_name,
                                "content": section_content,
                                "perspective": "ceo",
                            },
                            db,
                            session.user_id,
                        )
                    )
                    loop.close()
                    return result
                finally:
                    db.close()

            saved_count = 0
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {}
                for section, content in insights.items():
                    if content and content != "null" and isinstance(content, str):
                        futures[section] = executor.submit(_save_insight, section, content)

                for section, future in futures.items():
                    try:
                        future.result(timeout=15)
                        saved_count += 1
                    except Exception as save_err:
                        logger.warning("insight_save_error", section=section, error=str(save_err))

            logger.info(
                "insights_extracted_and_saved",
                session_id=session_id,
                entity_id=entity_id,
                saved_count=saved_count,
                sections=list(k for k, v in insights.items() if v and v != "null"),
            )

        except json.JSONDecodeError as je:
            logger.warning("insight_extraction_json_error", error=str(je), raw=raw[:200] if raw else "empty")
        except Exception as e:
            logger.warning("insight_extraction_error", error=str(e))

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
