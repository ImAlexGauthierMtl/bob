"""Bob Chat Agent — conversational CRM assistant powered by Qwen3 32B.

Manages chat sessions with conversation history and CRM-aware system prompt.
Uses the existing LLMClient wrapper with model override for Qwen3.
"""

import json
import re
import time
from typing import Optional
from threading import Lock
import uuid

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

## CRM Procedures — FOLLOW THESE STRICTLY

### Searching Existing Entities
When the user asks to FIND, SEARCH, LOOK UP an entity (e.g., "cherche Bell Canada", "find the Bell account"):

1. Call `search_organizations` or `search_contacts` with the search query — this will open a search popup in the UI with numbered results from the CRM database
2. Tell the user what was found and ask them to pick by number
3. When they pick a number, use `ui_select_result` with the chosen index (or call `search_and_open_entity` to navigate directly)

### Creating an Opportunity (STRICT MULTI-STEP FLOW)
When the user asks to CREATE/ADD an opportunity:

YOU MUST follow these steps IN ORDER — do NOT skip any step:

1. **Identify the organization**: If the user mentions a company name, call `search_organizations` to find it. This opens a search popup. Tell the user the results and ask them to confirm which one (e.g., "J'ai trouvé 2 résultats: #1 Bell Canada Central Office, #2 Bell Canada Montreal. Lequel?"). WAIT for their answer.
2. **Identify the contact**: After the org is confirmed, ask the user for a contact name and email. If the contact doesn't exist yet, tell the user you'll create it. Call `create_contact` with the org_id.
3. **Create the opportunity**: Call `create_opportunity` with the name, organization_id, and contact_id.
4. **Link products** (optional): If the user mentions a product, call `link_product_to_opportunity`.

IMPORTANT RULES:
- NEVER call `create_opportunity` without first resolving the organization_id from a search
- NEVER skip the contact step — always ask if a contact should be associated
- NEVER use `open_create_dialog` for creating opportunities — ONLY use the API tools

### Creating Other Entities (Organization + Contact)
When the user asks to CREATE, ADD, or NEW an organization or contact:

1. **Ask for missing required info** before executing:
   - Organization: name (REQUIRED), domain, industry
   - Contact: first_name + last_name (REQUIRED), email, phone, organization_id
2. **Execute** using API tools: `create_organization`, `create_contact`
3. **Confirm** to the user what was created

### Tool Priority Rules
- For **CREATING**: use `create_organization`, `create_contact`, `create_opportunity`, `link_product_to_opportunity`
- For **SEARCHING/FINDING**: use `search_organizations`, `search_contacts` (these automatically open the search popup UI)
- For **OPENING a specific record**: use `search_and_open_entity`
- NEVER use `open_create_dialog` — it opens the Google Maps add dialog, not a search

### Handling Ambiguous Requests
If the user says something like "ajoute le compte X avec contact Y et une opportunité Z":
- X is the **organization** name
- Y is the **contact** name (split into first_name / last_name)
- Z is the **opportunity** name
- Ask the user for any missing details (email, value, stage) BEFORE executing

UI Controls (for navigation only):
- When the user says "choose number X", "select the second one", use `ui_select_result` with the requested index.

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
_THINK_SLASH_RE = re.compile(r"/?(?:no_)?think\b", re.IGNORECASE)
_THINK_PIPE_RE = re.compile(r"<\|/?think\|>", re.IGNORECASE)


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
        # Intent Router: paused workflow state for multi-turn flows
        self.workflow_state: Optional[dict] = None
        self.workflow_resume_key: Optional[str] = None

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
        """Get existing session or create a new one.

        Session isolation: sessions are scoped to tenant_id:user_id.
        A user can only access their own sessions within their tenant.
        """
        # Build isolation key: tenant:user:session
        isolation_key = f"{tenant_id}:{user_id}:{session_id}"

        with self._lock:
            # Cleanup expired sessions
            self._cleanup_expired()

            if isolation_key not in self._sessions:
                self._sessions[isolation_key] = ChatSession(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    user_email=user_email,
                    mission_prompt=mission_prompt,
                    mission_context=mission_context,
                )
                logger.info(
                    "bob_session_created",
                    session_id=session_id,
                    isolation_key=isolation_key,
                    user=user_email,
                    has_mission=mission_prompt is not None,
                )

            return self._sessions[isolation_key]

    # Removed local TOOLS list; imported dynamically in chat()

    def chat(
        self,
        session_id: str,
        user_message: str,
        tenant_id: str = "",
        user_id: str = "",
    ) -> tuple[str, list[dict]]:
        """Send a message to Bob and get a response + optional actions.

        Args:
            session_id: Session identifier
            user_message: The user's message text
            tenant_id: Optional tenant for isolation key
            user_id: Optional user for isolation key

        Returns:
            Tuple of (response_text, actions_list)
        """
        isolation_key = f"{tenant_id}:{user_id}:{session_id}" if tenant_id and user_id else session_id
        session = self._sessions.get(isolation_key)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.add_user_message(user_message)

        # ── Generate intent correlation ──────────────
        intent_id = str(uuid.uuid4())
        intent_label = user_message[:80].strip()

        # ═══════════════════════════════════════════════════════
        # INTENT ROUTER — classify first, workflow if applicable
        # Falls back to legacy 18-tool flow for general_chat
        # and mission mode conversations.
        # ═══════════════════════════════════════════════════════
        if not session.mission_prompt:  # Skip router for mission/BCC mode
            try:
                workflow_result = self._try_intent_workflow(
                    session=session,
                    user_message=user_message,
                    session_id=session_id,
                    intent_id=intent_id,
                    intent_label=intent_label,
                )
                if workflow_result is not None:
                    text, actions, tool_steps = workflow_result
                    session.add_assistant_message(text)
                    logger.info(
                        "intent_router_handled",
                        session_id=session_id,
                        actions=len(actions),
                        tools=len(tool_steps),
                    )
                    return text, actions, tool_steps
            except Exception as wr_err:
                logger.warning("intent_router_fallback", error=str(wr_err))
                # Fall through to legacy flow

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

        # ── Inject BCC task procedures ──────────────
        bcc_procedures = ""
        org_context = ""
        try:
            from app.infrastructure.database import SessionLocal as BccSessionLocal
            from app.domain.entities.bcc_entities import BccTask, BccTaskTemplate, BccOrganization, BccIntent, BccProfileEntry
            from app.domain.entities.user import User
            db_bcc = BccSessionLocal()
            try:
                # ── Resolve active organization ──────────
                active_org_id = None
                user_row = db_bcc.query(User).filter(User.id == session.user_id).first()
                if user_row and user_row.active_organization_id:
                    active_org_id = user_row.active_organization_id
                    org = db_bcc.query(BccOrganization).filter(
                        BccOrganization.id == active_org_id
                    ).first()
                    if org:
                        org_lines = ["\n\n## Active Organization Context:"]
                        org_lines.append(f"**Organization:** {org.name}")
                        if org.description:
                            org_lines.append(f"{org.description}")

                        # Load vision/mission/culture/competition from bcc_profile_entries
                        entries = db_bcc.query(BccProfileEntry).filter(
                            BccProfileEntry.entity_type == "organization",
                            BccProfileEntry.entity_id == active_org_id,
                            BccProfileEntry.is_active == True,
                            BccProfileEntry.section.in_(["vision", "mission", "culture", "competition"]),
                        ).all()
                        section_map = {e.section: e.content for e in entries}
                        for key in ("vision", "mission", "culture", "competition"):
                            if section_map.get(key):
                                org_lines.append(f"**{key.capitalize()}:** {section_map[key]}")

                        # Load org profile (location, domains)
                        if org.profile:
                            op = org.profile
                            if op.operations_domains:
                                org_lines.append(f"**Domains:** {', '.join(op.operations_domains)}")

                        # Load org intents
                        intents = db_bcc.query(BccIntent).filter(
                            BccIntent.tenant_id == session.tenant_id
                        ).all()
                        if intents:
                            org_lines.append("\n### Available Intents:")
                            for intent in intents:
                                task_names = [
                                    link.task_template.name
                                    for link in sorted(intent.task_links, key=lambda x: x.sort_order)
                                    if link.task_template
                                ]
                                org_lines.append(f"- **{intent.name}** ({intent.category}): {' → '.join(task_names)}")
                                if intent.trigger_phrases:
                                    phrases = ', '.join(f'"{p}"' for p in intent.trigger_phrases[:3])
                                    org_lines.append(f"  Triggers: {phrases}")

                        org_context = "\n".join(org_lines)
                        logger.info("org_context_injected", org_name=org.name, org_id=active_org_id)


                lines = ["\n\n## Procedural Knowledge (from Control Center):"]
                has_content = False

                # Load role-specific tasks with steps
                tasks = db_bcc.query(BccTask).filter(
                    BccTask.tenant_id == session.tenant_id
                ).all()
                for t in tasks:
                    has_content = True
                    lines.append(f"\n### Task: {t.name}")
                    if t.description:
                        lines.append(f"{t.description}")
                    if t.steps:
                        for step in t.steps:
                            lines.append(f"  {step.step_number}. {step.instruction}")
                            if step.details:
                                lines.append(f"     Details: {step.details}")

                # Load library task templates with procedures
                templates = db_bcc.query(BccTaskTemplate).filter(
                    BccTaskTemplate.tenant_id == session.tenant_id
                ).all()
                for tpl in templates:
                    ctx = tpl.context or {}
                    procedure = ctx.get("procedure")
                    if procedure:
                        has_content = True
                        lines.append(f"\n### Procedure: {tpl.name}")
                        if tpl.description:
                            lines.append(f"{tpl.description}")
                        for step_text in procedure:
                            lines.append(f"  {step_text}")
                        tool_prio = ctx.get("tool_priority")
                        if tool_prio:
                            lines.append(f"  ⚠ {tool_prio}")

                if has_content:
                    bcc_procedures = "\n".join(lines)
            finally:
                db_bcc.close()
        except Exception as bcc_err:
            logger.warning("bcc_task_injection_failed", error=str(bcc_err))

        system_prompt = BOB_SYSTEM_PROMPT + personality_directives + org_context + bcc_procedures

        # ── First-turn greeting — use user's first name ─────────
        if session.turn_count == 1:
            # Extract first name from email or user row
            first_name = ""
            try:
                from app.infrastructure.database import SessionLocal as _GS
                from app.domain.entities.user import User as _U
                _db = _GS()
                try:
                    _u = _db.query(_U).filter(_U.id == session.user_id).first()
                    if _u and _u.first_name:
                        first_name = _u.first_name
                    elif session.user_email:
                        first_name = session.user_email.split("@")[0].split(".")[0].capitalize()
                finally:
                    _db.close()
            except Exception:
                pass
            if first_name:
                system_prompt += f"\n\nIMPORTANT: This is the very FIRST message of the session. Start your response with a short, natural greeting using the user's first name: \"{first_name}\". Example: \"Hi {first_name}!\" or \"Hey {first_name}!\" — one short line only. Do NOT introduce yourself or explain what you do. Just the greeting, then get to the point."


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

            try:
                response = client.chat.completions.create(
                    model=settings.bob_model,
                    messages=messages,
                    tools=active_tools,
                    tool_choice="auto",
                    temperature=llm_temperature,
                    max_tokens=2048,
                )
            except Exception as tool_err:
                if "tool_use_failed" not in str(tool_err):
                    raise
                # Groq tool_use_failed — retry once with tools
                logger.warning(
                    "bob_tool_use_retry",
                    session_id=session_id,
                    attempt=2,
                )
                try:
                    response = client.chat.completions.create(
                        model=settings.bob_model,
                        messages=messages,
                        tools=active_tools,
                        tool_choice="auto",
                        temperature=max(0.3, llm_temperature),
                        max_tokens=2048,
                    )
                except Exception:
                    # Last resort: text-only response
                    logger.warning(
                        "bob_tool_use_fallback_text",
                        session_id=session_id,
                    )
                    response = client.chat.completions.create(
                        model=settings.bob_model,
                        messages=messages,
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

            # ── Track LLM usage ────────────────────────
            try:
                from app.infrastructure.database import SessionLocal
                from app.middleware.usage_tracker import UsageTracker
                from app.domain.entities.usage_transaction import TriggerSource

                _track_db = SessionLocal()
                try:
                    _tracker = UsageTracker(_track_db)
                    _tokens_in = response.usage.prompt_tokens if response.usage else 0
                    _tokens_out = response.usage.completion_tokens if response.usage else 0
                    # Extract thinking block from raw content
                    _raw_content = choice.message.content or ""
                    _think_match = _THINK_RE.search(_raw_content)
                    _thinking = _think_match.group(0)[:500] if _think_match else None
                    _clean_content = _THINK_RE.sub("", _raw_content).strip()

                    _tool_calls_meta = None
                    if tool_calls:
                        _tool_calls_meta = [
                            {
                                "name": tc.function.name,
                                "args": tc.function.arguments[:300],
                            }
                            for tc in tool_calls
                        ]

                    _tracker.track_llm(
                        tenant_id=session.tenant_id,
                        user_id=session.user_id,
                        user_email=session.user_email,
                        model=settings.bob_model,
                        input_tokens=_tokens_in,
                        output_tokens=_tokens_out,
                        trigger_source=TriggerSource.BOB_CHAT,
                        trigger_id=session_id,
                        correlation_id=intent_id,
                        correlation_label=intent_label,
                        metadata={
                            "user_message": user_message[:500],
                            "response": _clean_content[:500],
                            "thinking": _thinking,
                            "tool_calls": _tool_calls_meta,
                            "finish_reason": finish_reason,
                        },
                    )
                finally:
                    _track_db.close()
            except Exception as _track_err:
                logger.warning("bob_usage_tracking_failed", error=str(_track_err))

            # Handle tool calls — loop to support multi-step tool chains
            MAX_TOOL_ROUNDS = 5
            tool_round = 0
            current_choice = choice
            tool_steps: list[dict] = []

            while current_choice.message.tool_calls and tool_round < MAX_TOOL_ROUNDS:
                tool_round += 1
                # Process each tool call
                tool_results: dict[str, str] = {}
                for tc in current_choice.message.tool_calls:
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
                                    "intent_id": intent_id,
                                    "intent_label": intent_label,
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
                    elif fn in ("search_organizations", "search_contacts"):
                        # Execute the search + also open UI popup
                        import concurrent.futures
                        import asyncio
                        from app.agents.tool_executor import execute_bob_tool
                        from app.infrastructure.database import SessionLocal as _SLS

                        def _run_search():
                            _db = _SLS()
                            try:
                                _loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(_loop)
                                _ctx = {
                                    "user_id": session.user_id,
                                    "tenant_id": session.tenant_id,
                                    "session_id": session_id,
                                    "intent_id": intent_id,
                                    "intent_label": intent_label,
                                }
                                res = _loop.run_until_complete(
                                    execute_bob_tool(fn, args, _ctx, _db)
                                )
                                _loop.close()
                                return res
                            finally:
                                _db.close()

                        with concurrent.futures.ThreadPoolExecutor() as _exec:
                            _fut = _exec.submit(_run_search)
                            _sresult = _fut.result(timeout=10)

                        tool_results[tc.id] = json.dumps(_sresult) if isinstance(_sresult, dict) else str(_sresult or '{"status": "no results"}')

                        # Also open the UI search dialog with query
                        _etype = "organization" if fn == "search_organizations" else "contact"
                        _pmap = {"organization": "organizations", "contact": "contacts"}
                        _sq = args.get("query", "")
                        actions.append({
                            "type": "search_entity",
                            "entity": _etype,
                            "page": _pmap.get(_etype, "contacts"),
                            "name": _sq,
                        })
                        actions.append({
                            "type": "ui_update_input",
                            "text": _sq,
                            "submit": True,
                        })
                        logger.info("search_with_ui_popup", tool=fn, query=_sq)
                    elif fn == "create_organization":
                        # ── INTERCEPTOR: check if org already exists before creating ──
                        import concurrent.futures as _cf_co
                        import asyncio as _aio_co
                        from app.infrastructure.database import SessionLocal as _SL_CO
                        from app.domain.entities.organization import Organization as _Org

                        _org_name = args.get("name", "")
                        _co_db = _SL_CO()
                        try:
                            _existing = _co_db.query(_Org).filter(
                                _Org.tenant_id == session.tenant_id,
                                _Org.name.ilike(f"%{_org_name}%")
                            ).limit(5).all()
                        finally:
                            _co_db.close()

                        if _existing:
                            # Org(s) found — emit search popup + return org data to LLM
                            _results = [
                                {"id": str(o.id), "name": o.name, "industry": o.industry, "phone": o.phone}
                                for o in _existing
                            ]
                            actions.append({
                                "type": "search_entity",
                                "entity": "organization",
                                "page": "organizations",
                                "name": _org_name,
                            })
                            actions.append({
                                "type": "ui_update_input",
                                "text": _org_name,
                                "submit": True,
                            })
                            tool_results[tc.id] = json.dumps({
                                "status": "already_exists",
                                "message": f"Organization(s) matching '{_org_name}' already exist in the CRM. Use the existing org_id instead of creating a duplicate.",
                                "existing_organizations": _results,
                            })
                            logger.info("create_org_intercepted_existing", name=_org_name, count=len(_existing))
                        else:
                            # No match — proceed with normal creation
                            from app.agents.tool_executor import execute_bob_tool as _exec_co

                            def _run_create_org():
                                _db2 = _SL_CO()
                                try:
                                    _loop2 = _aio_co.new_event_loop()
                                    _aio_co.set_event_loop(_loop2)
                                    _ctx2 = {
                                        "user_id": session.user_id,
                                        "tenant_id": session.tenant_id,
                                        "session_id": session_id,
                                        "intent_id": intent_id,
                                        "intent_label": intent_label,
                                    }
                                    _r = _loop2.run_until_complete(_exec_co(fn, args, _ctx2, _db2))
                                    _loop2.close()
                                    return json.dumps(_r)
                                finally:
                                    _db2.close()

                            with _cf_co.ThreadPoolExecutor() as _ex_co:
                                _fut_co = _ex_co.submit(_run_create_org)
                                tool_results[tc.id] = _fut_co.result(timeout=30)
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
                                    "intent_id": intent_id,
                                    "intent_label": intent_label,
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

                    tool_steps.append({"tool": fn, "status": "ok"})
                    logger.info(
                        "bob_tool_call",
                        session_id=session_id,
                        function=fn,
                        arguments=args,
                        round=tool_round,
                    )

                # Add tool call + result to context
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": current_choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in current_choice.message.tool_calls
                    ],
                }
                messages.append(assistant_msg)
                for tc in current_choice.message.tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_results.get(tc.id, '{"status": "ok"}'),
                    })

                # Get the follow-up response (with tools so it can chain)
                followup = client.chat.completions.create(
                    model=settings.bob_model,
                    messages=messages,
                    tools=active_tools,
                    tool_choice="auto",
                    temperature=settings.bob_temperature,
                    max_tokens=2048,
                )
                current_choice = followup.choices[0]

                # Track follow-up usage
                try:
                    from app.infrastructure.database import SessionLocal as _SL2
                    from app.middleware.usage_tracker import UsageTracker as _UT2
                    from app.domain.entities.usage_transaction import TriggerSource as _TS2

                    _fu_db = _SL2()
                    try:
                        _fu_tokens_in = followup.usage.prompt_tokens if followup.usage else 0
                        _fu_tokens_out = followup.usage.completion_tokens if followup.usage else 0
                        _fu_tracker = _UT2(_fu_db)
                        _fu_tracker.track_llm(
                            tenant_id=session.tenant_id,
                            user_id=session.user_id,
                            user_email=session.user_email,
                            model=settings.bob_model,
                            input_tokens=_fu_tokens_in,
                            output_tokens=_fu_tokens_out,
                            trigger_source=_TS2.BOB_CHAT,
                            trigger_id=session_id,
                            correlation_id=intent_id,
                            correlation_label=intent_label,
                            metadata={
                                "type": "follow_up",
                                "round": tool_round,
                                "response": (current_choice.message.content or "")[:500],
                                "tool_results": {k: v[:300] for k, v in list(tool_results.items())[:5]},
                            },
                        )
                    finally:
                        _fu_db.close()
                except Exception as _fu_err:
                    logger.warning("bob_followup_tracking_failed", error=str(_fu_err))

            # Final response text — if loop exhausted max rounds with pending
            # tool calls, force a final text-only response
            response_text = current_choice.message.content or ""
            if not response_text.strip() and tool_round >= MAX_TOOL_ROUNDS:
                logger.info("bob_tool_loop_exhausted", rounds=tool_round, session_id=session_id)
                final_resp = client.chat.completions.create(
                    model=settings.bob_model,
                    messages=messages,
                    temperature=settings.bob_temperature,
                    max_tokens=512,
                )
                response_text = final_resp.choices[0].message.content or ""

            # Strip <think>...</think> blocks + /think, /no_think artifacts
            response_text = _THINK_RE.sub("", response_text)
            response_text = _THINK_SLASH_RE.sub("", response_text)
            response_text = _THINK_PIPE_RE.sub("", response_text)
            response_text = response_text.strip()


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

            return response_text, actions, tool_steps

        except Exception as e:
            logger.error(
                "bob_chat_error",
                session_id=session_id,
                error=str(e),
            )
            raise

    def _try_intent_workflow(
        self,
        session: "ChatSession",
        user_message: str,
        session_id: str,
        intent_id: str,
        intent_label: str,
    ) -> Optional[tuple[str, list[dict], list[dict]]]:
        """Try to handle the message via Intent Router workflows.

        Returns (text, actions, tool_steps) if handled,
        or None to fall back to legacy 18-tool flow.
        """
        from app.infrastructure.database import SessionLocal
        from app.agents.workflow_engine import (
            WorkflowContext,
            get_workflow,
            get_resume_handler,
        )

        # ── 1. Check for paused workflow (resume) ──
        if session.workflow_resume_key and session.workflow_state is not None:
            handler = get_resume_handler(session.workflow_resume_key)
            if handler:
                db = SessionLocal()
                try:
                    # Create a lightweight entities obj from saved state
                    from app.agents.intent_classifier import ExtractedEntities
                    saved = session.workflow_state.get("original_entities", {})
                    entities = ExtractedEntities(
                        contact_first=saved.get("contact_first"),
                        contact_last=saved.get("contact_last"),
                        email=saved.get("email"),
                        phone=saved.get("phone"),
                        product_name=saved.get("product_name"),
                        quantity=saved.get("quantity"),
                        amount=saved.get("amount"),
                    )

                    ctx = WorkflowContext(
                        db=db,
                        tenant_id=session.tenant_id,
                        user_id=session.user_id,
                        user_email=session.user_email,
                        entities=entities,
                        user_message=user_message,
                        state=dict(session.workflow_state),
                    )

                    result = handler(ctx)

                    # Update session state
                    if result.paused:
                        session.workflow_state = result.state
                        session.workflow_resume_key = result.resume_key
                    else:
                        session.workflow_state = None
                        session.workflow_resume_key = None

                    logger.info(
                        "workflow_resumed",
                        resume_key=session.workflow_resume_key,
                        paused=result.paused,
                        actions=len(result.actions),
                    )
                    return result.message, result.actions, result.tool_steps
                finally:
                    db.close()

        # ── 2. Classify intent ──
        from app.agents.intent_classifier import classify_message

        classification = classify_message(
            message=user_message,
            conversation_context=session.messages[-4:] if session.messages else None,
        )

        logger.info(
            "intent_classified_for_routing",
            intent=classification.intent,
            session_id=session_id,
        )

        # ── 3. Route to workflow or fall back ──
        if classification.intent == "general_chat":
            return None  # Fall back to legacy 18-tool flow

        wf = get_workflow(classification.intent)
        if not wf:
            return None  # Unknown intent — legacy flow

        db = SessionLocal()
        try:
            ctx = WorkflowContext(
                db=db,
                tenant_id=session.tenant_id,
                user_id=session.user_id,
                user_email=session.user_email,
                entities=classification.entities,
                user_message=user_message,
            )

            result = wf(ctx)

            # Store pause state in session
            if result.paused:
                session.workflow_state = result.state
                session.workflow_resume_key = result.resume_key
            else:
                session.workflow_state = None
                session.workflow_resume_key = None

            logger.info(
                "workflow_executed",
                intent=classification.intent,
                paused=result.paused,
                actions=len(result.actions),
                tools=len(result.tool_steps),
            )
            return result.message, result.actions, result.tool_steps
        finally:
            db.close()

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

    def delete_session(self, session_id: str, tenant_id: str = "", user_id: str = "") -> bool:
        """Delete a specific session (with isolation check)."""
        isolation_key = f"{tenant_id}:{user_id}:{session_id}" if tenant_id and user_id else session_id
        with self._lock:
            if isolation_key in self._sessions:
                del self._sessions[isolation_key]
                logger.info("bob_session_deleted", session_id=session_id, isolation_key=isolation_key)
                return True
            return False

    def get_session_info(self, session_id: str, tenant_id: str = "", user_id: str = "") -> Optional[dict]:
        """Get session metadata (with isolation check)."""
        isolation_key = f"{tenant_id}:{user_id}:{session_id}" if tenant_id and user_id else session_id
        session = self._sessions.get(isolation_key)
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

    def list_sessions(self, user_id: str, tenant_id: str = "") -> list[dict]:
        """List all active sessions for a user within their tenant."""
        prefix = f"{tenant_id}:{user_id}:" if tenant_id else ""
        with self._lock:
            self._cleanup_expired()
            results = []
            for key, s in self._sessions.items():
                if prefix and key.startswith(prefix):
                    original_sid = key[len(prefix):]
                    info = self.get_session_info(original_sid, tenant_id, user_id)
                    if info:
                        results.append(info)
                elif not prefix and s.user_id == user_id:
                    info = self.get_session_info(key)
                    if info:
                        results.append(info)
            return results

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
