"""Bob Voice Pipeline — Pipecat STT → LLM → TTS pipeline builder.

Constructs a Pipecat pipeline using Groq services for real-time
voice conversation with Bob. Supports barge-in via Silero VAD.

Note: Pipecat imports are lazy (inside the function) so the app
can start without pipecat installed. Install with:
    pip install pipecat-ai[groq,silero,websocket]
"""

import structlog

from app.config import settings
from app.voice.voice_session import VoiceSession

logger = structlog.get_logger(__name__)

BOB_VOICE_SYSTEM_PROMPT = """# ── Role Context ─────────────────
- You are Bob, an elite AI assistant for the Croo Digital Experience CRM.
- Your capabilities include answering questions, navigating the CRM, creating records, and initiating training modules.
- CRITICAL: If the user asks for their training (e.g. "ma formation CRM", "start training") or complains the presentation isn't showing ("ne montre pas la présentation", "I don't see the presentation"), you MUST immediately call the `start_crm_training` tool. Do NOT just say "I don't see it". Let the tool do the navigation.
- You are having a real-time voice conversation with a user.

Your capabilities:
- Answer questions about CRM data and best practices
- Help users manage contacts, organizations, opportunities
- Provide insights about sales pipelines
- Assist with workflow automation
- NAVIGATE the user in the application using tools
- OPEN create dialogs for new entities using tools

When the user asks to go somewhere or create something, USE YOUR TOOLS:
- "go to contacts" → call navigate_to with page="contacts"
- "add an organization" → call open_create_dialog with entity="organization"
- "new opportunity" → call open_create_dialog with entity="opportunity"
- "I want to do my CRM training" → call start_crm_training
- "let's start the training" → call start_crm_training
- "create a new user" → call navigate_to with page="settings" and explain that user management defaults to the UI for security reasons.

UI Control & Chaining:
- To correct a misheard spelling in a search/create dialog: call `ui_update_input` with the corrected text. Use submit=true if the user is done dictating.
- To select a specific numbered result from a list (e.g., "choose number 2", "prends le premier"): call `ui_select_result` with index=2 or 1.
- Chaining: if the user asks to create an organization and then add a contact to it, you can navigate them step by step or use multiple tool calls. Guide them fluidly.

After calling a tool, confirm what you did briefly (e.g. "Done, I've opened the contacts page for you.").

Communication style for VOICE:
- Keep responses SHORT (1-3 sentences max for voice)
- Be conversational and natural
- ABSOLUTELY NO MARKDOWN: never use *, **, #, ##, bullet points, or any formatting characters.
  The TTS engine reads them literally as spoken text — "asterisk asterisk name asterisk asterisk"
  sounds terrible. Use plain text only.
- If a question needs a long answer, give the key point first, then offer to elaborate
- Use natural language fillers when appropriate ("Sure thing", "Let me check", etc.)
- NEVER use <think> tags or internal reasoning — respond directly
- Do NOT think out loud — go straight to your answer

EMOTIONAL EXPRESSIVENESS (Orpheus TTS vocal directions):
Your text output is spoken aloud by an expressive TTS engine. You can make your voice more
natural and human-like by embedding vocal direction tags in your responses.

Available tags:
- Bracket directions: [cheerful], [warm], [friendly], [excited], [whisper], [professionally],
  [confidently], [concerned], [sympathetic], [sarcastic], [dramatic]
- Inline sounds: <laugh>, <chuckle>, <sigh>, <gasp>
- Combined: [cheerful] text [dropping tone] more text

Rules for using emotion tags:
- Place tags BEFORE the text they should affect
- Use them SPARINGLY — max 1-2 tags per response for natural feel
- NEVER explain the tags; they are invisible to the user
- Match emotions to CONTEXT: good news → [cheerful], confirmations → [warm],
  errors → [concerned], greetings → [friendly], jokes → <chuckle>
- Omit tags entirely when the default conversational tone is appropriate
- Do NOT force emotions — natural > theatrical

Language: Match the user's language. French if they speak French, English if English.

/no_think"""


async def create_bob_voice_pipeline(
    websocket,
    session: VoiceSession,
    user_id: str = "",
) -> tuple:
    """Build a Pipecat pipeline for Bob voice conversation.

    Args:
        websocket: The FastAPI WebSocket connection
        session: The voice session for this connection
        user_id: The user ID for reading saved voice settings

    Returns:
        Tuple of (PipelineTask, PipelineRunner) ready to run
    """
    # Lazy imports — pipecat is only needed when a voice session starts
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.services.groq.stt import GroqSTTService
    from pipecat.services.groq.llm import GroqLLMService
    from pipecat.services.groq.tts import GroqTTSService
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketTransport,
        FastAPIWebsocketParams,
    )
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.frames.frames import LLMMessagesFrame
    from pipecat.serializers.protobuf import ProtobufFrameSerializer

    # ── Transport ────────────────────────────────────────
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            audio_in_sample_rate=16000,   # Whisper expects 16kHz
            audio_out_sample_rate=24000,  # Orpheus TTS outputs 24kHz
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.3,
                    min_volume=0.3,
                ),
            ),
            vad_audio_passthrough=True,
            serializer=ProtobufFrameSerializer(
                params=ProtobufFrameSerializer.InputParams(ignore_rtvi_messages=False),
            ),
            session_timeout=settings.voice_max_session_minutes * 60,
        ),
    )

    # ── STT (Whisper on Groq) ────────────────────────────
    stt = GroqSTTService(
        api_key=settings.groq_api_key,
        model=settings.groq_whisper_model,
    )

    # ── LLM (Llama 3.3 70B on Groq) ─────────────────────────
    from app.agents.bob_tools import BOB_TOOLS
    tools = BOB_TOOLS

    llm = GroqLLMService(
        api_key=settings.groq_api_key,
        model=settings.bob_model,
    )

    # ── DEBUG: trace what gets sent to the API ───────────
    _orig_process_context = llm._process_context

    async def _debug_process_context(context):
        tools_count = len(context.tools) if context.tools else 0
        msg_count = len(context.messages) if hasattr(context, "messages") else 0
        last_msg = context.messages[-1] if hasattr(context, "messages") and context.messages else None
        logger.info(
            "voice_llm_api_call_debug",
            tools_count=tools_count,
            tool_choice=str(context.tool_choice) if hasattr(context, "tool_choice") else "N/A",
            message_count=msg_count,
            last_user_msg=str(last_msg)[:200] if last_msg else "None",
            session_id=session.session_id,
        )
        return await _orig_process_context(context)

    llm._process_context = _debug_process_context

    # ── Function call handlers ───────────────────────────
    task_ref: list = []  # mutable container — filled after PipelineTask creation

    async def handle_any_tool(params):
        fn = params.function_name
        args = params.arguments
        logger.info("bob_voice_tool_call", session_id=session.session_id, function=fn, arguments=args)

        if fn == "navigate_to":
            page = args.get("page", "dashboard")
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                action = {"type": "bob_action", "action": {"type": "navigate", "page": page}}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=action))
            await params.result_callback({"status": "ok", "action": "navigate", "page": page})
            
        elif fn == "open_create_dialog":
            entity = args.get("entity", "contact")
            name = args.get("name")
            page_map = {
                "organization": "organizations", "contact": "contacts",
                "opportunity": "opportunities", "quote": "quotes", "activity": "activities",
            }
            page = page_map.get(entity, "contacts")
            action: dict = {"type": "open_create_dialog", "entity": entity, "page": page}
            if name:
                action["name"] = name
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                server_msg = {"type": "bob_action", "action": action}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
            result = {"status": "ok", "action": "open_create_dialog", "entity": entity, "page": page}
            if name: result["name"] = name
            await params.result_callback(result)
            
        elif fn == "start_crm_training":
            page = "template/crm-mastery"
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                action = {"type": "bob_action", "action": {"type": "navigate", "page": page}}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=action))
            await params.result_callback({"status": "ok", "action": "navigate", "page": page})
            
        elif fn == "change_training_slide":
            action_dict = {
                "type": "change_slide",
                "direction": args.get("direction", "next"),
            }
            slide_num = args.get("slide_number")
            if slide_num is not None:
                action_dict["slide_number"] = slide_num
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                server_msg = {"type": "bob_action", "action": action_dict}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
            await params.result_callback({"status": "ok"})
            
        elif fn == "ui_update_input":
            action_dict = {
                "type": "ui_update_input",
                "text": args.get("text", ""),
                "submit": args.get("submit", False)
            }
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                server_msg = {"type": "bob_action", "action": action_dict}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
            await params.result_callback({"status": "ok"})
            
        elif fn == "ui_select_result":
            action_dict = {
                "type": "ui_select_result",
                "index": args.get("index", 1)
            }
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                server_msg = {"type": "bob_action", "action": action_dict}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
            await params.result_callback({"status": "ok"})

        elif fn == "ui_switch_tab":
            action_dict = {
                "type": "ui_switch_tab",
                "tab_name": args.get("tab_name", ""),
            }
            if task_ref:
                from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                server_msg = {"type": "bob_action", "action": action_dict}
                await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
            await params.result_callback({"status": "ok"})
            
        else:
            # Execute backend CRM tool
            from app.agents.tool_executor import execute_bob_tool
            from app.infrastructure.database import SessionLocal
            db = SessionLocal()
            try:
                user_context = {
                    "user_id": user_id,
                    "tenant_id": session.tenant_id,
                    "session_id": session.session_id,
                }
                result = await execute_bob_tool(fn, args, user_context, db)

                # Catch dynamic actions returned from tools (like navigate from search_and_open_entity)
                if result and isinstance(result, dict) and result.get("status") == "ok" and "action" in result:
                    if task_ref:
                        from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
                        ui_action = result.copy()
                        ui_action.pop("status", None)
                        ui_action.pop("message", None)
                        ui_action.pop("results", None)
                        ui_action["type"] = ui_action.pop("action")
                        server_msg = {"type": "bob_action", "action": ui_action}
                        await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))

                await params.result_callback(result)
            except Exception as e:
                logger.error("voice_tool_error", error=str(e), function=fn)
                await params.result_callback({"status": "error", "message": "Backend error"})
            finally:
                db.close()

    for t in tools:
        fn_name = t["function"]["name"]
        llm.register_function(fn_name, handle_any_tool)

    # ── TTS (Orpheus on Groq) ────────────────────────────
    # Read user's saved voice/personality preferences from DB
    tts_voice = settings.groq_tts_voice  # default from config
    tts_speed = 1.0
    personality_directives = ""
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bob_settings import BobUserSettings
        db = SessionLocal()
        try:
            user_settings = BobUserSettings.get_or_create(db, user_id)
            tts_voice = user_settings.voice or tts_voice
            tts_speed = user_settings.speed or 1.0

            # Build personality directives from saved settings
            tone_map = {
                "professional": "Professional and clear",
                "friendly": "Warm, friendly and approachable",
                "casual": "Casual and relaxed",
                "formal": "Formal and polished",
            }
            length_map = {
                "concise": "Keep responses very short (1 sentence when possible).",
                "balanced": "Keep responses short (1-3 sentences for voice).",
                "detailed": "Give thorough responses but stay conversational.",
            }
            # Emotion expressiveness mapped to tone
            emotion_map = {
                "professional": (
                    "Use emotion tags very sparingly — only [professionally] or [confidently] "
                    "when appropriate. Keep a composed, polished tone. Avoid laughs or sighs."
                ),
                "friendly": (
                    "Use emotion tags naturally to create warmth: [cheerful] for good news, "
                    "[warm] for greetings, <chuckle> when lighthearted, [concerned] when "
                    "there's a problem. Aim for 1-2 tags per response."
                ),
                "casual": (
                    "Be expressive and lively! Use [excited] for great news, <laugh> or <chuckle> "
                    "freely, [whisper] for secrets, <sigh> when something is tedious, "
                    "[sarcastic] when the moment fits. Feel like a fun colleague."
                ),
                "formal": (
                    "Use emotion tags rarely. Only [formally] or [authoritatively] "
                    "when needed. Maintain a dignified, restrained vocal presence."
                ),
            }
            tone_desc = tone_map.get(user_settings.tone, "Professional and clear")
            length_desc = length_map.get(user_settings.response_length, "Keep responses short (1-3 sentences for voice).")
            emotion_desc = emotion_map.get(user_settings.tone, emotion_map["professional"])
            emoji_note = " You may use emoji when appropriate." if user_settings.emoji_usage else " Do NOT use emoji."

            personality_directives = f"""
Personality settings (from user preferences):
- Tone: {tone_desc}
- {length_desc}
- Formality level: {user_settings.formality:.1f}/1.0 (higher = more formal)
- Creativity: {user_settings.creativity:.1f}/1.0 (higher = more creative/varied responses){emoji_note}

Emotion expressiveness for your current tone:
{emotion_desc}
"""
            logger.info(
                "voice_using_user_settings",
                voice=tts_voice,
                speed=tts_speed,
                tone=user_settings.tone,
                user_id=user_id,
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning("voice_settings_lookup_failed", error=str(e))

    tts = GroqTTSService(
        api_key=settings.groq_api_key,
        voice_id=tts_voice,
        model_name=settings.groq_tts_model,
        params=GroqTTSService.InputParams(speed=tts_speed),
    )

    # ── BCC Context Injection ────────────────────────────
    bcc_context = ""
    try:
        from app.infrastructure.database import SessionLocal
        from app.agents.knowledge.knowledge_extractor import get_active_layer_profile_context
        db = SessionLocal()
        try:
            bcc_context = await get_active_layer_profile_context(
                db=db,
                context_type="tenant",
                context_id=session.tenant_id
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning("voice_bcc_context_lookup_failed", error=str(e))

    # ── LLM Context with system prompt ───────────────────
    system_prompt = BOB_VOICE_SYSTEM_PROMPT
    if bcc_context:
        system_prompt += f"\n\n# ── Organizational Context (BCC Profile) ──\n{bcc_context}\n"
    system_prompt += f"\n\n{personality_directives}"
    
    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Inject any existing conversation history from text chat
    for msg in session.messages:
        messages.append(msg)

    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    # (Think tag filter removed as Llama-3.3 doesn't output <think> tags like Qwen3)

    # ── Pipeline ─────────────────────────────────────────
    pipeline = Pipeline(
        [
            transport.input(),          # WebSocket audio in
            stt,                        # Speech-to-text
            context_aggregator.user(),  # Aggregate user transcript
            llm,                        # LLM response
            tts,                        # Text-to-speech
            transport.output(),         # WebSocket audio out
            context_aggregator.assistant(),  # Store assistant response
        ]
    )

    # ── RTVI config for function call reporting ─────────
    from pipecat.processors.frameworks.rtvi import (
        RTVIObserverParams,
        RTVIFunctionCallReportLevel,
    )

    rtvi_params = RTVIObserverParams(
        function_call_report_level={"*": RTVIFunctionCallReportLevel.FULL},
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        rtvi_observer_params=rtvi_params,
    )
    task_ref.append(task)  # make task accessible to function handlers

    # ── Event handlers ───────────────────────────────────
    @transport.event_handler("on_client_connected")
    async def on_connected(transport_instance, client):
        logger.info(
            "voice_client_connected",
            session_id=session.session_id,
            user=session.user_email,
        )
        # Send initial context to kick off the pipeline
        await task.queue_frames([LLMMessagesFrame(messages)])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport_instance, client):
        logger.info(
            "voice_client_disconnected",
            session_id=session.session_id,
            user=session.user_email,
        )
        # ── Track voice session usage ──
        try:
            import time
            from app.infrastructure.database import SessionLocal
            from app.middleware.usage_tracker import UsageTracker
            from app.domain.entities.usage_transaction import TriggerSource

            session_duration = time.time() - session.created_at if hasattr(session, "created_at") else 0
            _track_db = SessionLocal()
            try:
                _tracker = UsageTracker(_track_db)
                # STT usage — approximate from session duration
                if session_duration > 0:
                    _tracker.track_stt(
                        tenant_id=session.tenant_id,
                        user_id=user_id,
                        user_email=session.user_email,
                        model=settings.groq_whisper_model,
                        audio_seconds=session_duration,
                        trigger_source=TriggerSource.BOB_VOICE,
                        trigger_id=session.session_id,
                        correlation_id=session.session_id,
                    )
                    # TTS usage — approximate characters from message count
                    msg_count = len(session.messages) if hasattr(session, "messages") else 0
                    est_chars = msg_count * 100  # rough estimate per response
                    if est_chars > 0:
                        _tracker.track_tts(
                            tenant_id=session.tenant_id,
                            user_id=user_id,
                            user_email=session.user_email,
                            model=settings.groq_tts_model,
                            characters=est_chars,
                            trigger_source=TriggerSource.BOB_VOICE,
                            trigger_id=session.session_id,
                            correlation_id=session.session_id,
                        )
            finally:
                _track_db.close()
        except Exception as _track_err:
            logger.warning("voice_usage_tracking_failed", error=str(_track_err))

        session.close()

    runner = PipelineRunner()

    logger.info(
        "voice_pipeline_created",
        session_id=session.session_id,
        stt_model=settings.groq_whisper_model,
        llm_model=settings.bob_model,
        tts_model=settings.groq_tts_model,
        tts_voice=settings.groq_tts_voice,
    )

    return task, runner
