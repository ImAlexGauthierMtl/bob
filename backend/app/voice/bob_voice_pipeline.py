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

BOB_VOICE_SYSTEM_PROMPT = """You are Bob, an intelligent CRM assistant for Croo Digital Experience.
You are having a real-time voice conversation with a user.

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

After calling a tool, confirm what you did briefly (e.g. "Done, I've opened the contacts page for you.").

Communication style for VOICE:
- Keep responses SHORT (1-3 sentences max for voice)
- Be conversational and natural
- Avoid bullet points and markdown — you are speaking, not writing
- If a question needs a long answer, give the key point first, then offer to elaborate
- Use natural language fillers when appropriate ("Sure thing", "Let me check", etc.)
- NEVER use <think> tags or internal reasoning — respond directly
- Do NOT think out loud — go straight to your answer

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

    # ── LLM (Qwen3 32B on Groq) ─────────────────────────
    tools = [
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
                                "dashboard",
                                "organizations",
                                "contacts",
                                "opportunities",
                                "quotes",
                                "activities",
                                "settings",
                                "knowledge-base",
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
                                "organization",
                                "contact",
                                "opportunity",
                                "quote",
                                "activity",
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
    # New Pipecat API: handler receives FunctionCallParams.
    # MUST call params.result_callback(result) to push result back into pipeline.
    # We also push RTVIServerMessageFrame so the frontend gets the action
    # immediately via RTVIEvent.ServerMessage (RTVI function call events
    # are unreliable with the WebSocket transport).
    task_ref: list = []  # mutable container — filled after PipelineTask creation

    async def handle_navigate(params):
        page = params.arguments.get("page", "dashboard")
        logger.info("bob_action_navigate", page=page, session_id=session.session_id)
        # Push action to frontend via server message
        if task_ref:
            from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
            action = {"type": "bob_action", "action": {"type": "navigate", "page": page}}
            await task_ref[0].queue_frame(RTVIServerMessageFrame(data=action))
        await params.result_callback({"status": "ok", "action": "navigate", "page": page})

    async def handle_create_dialog(params):
        entity = params.arguments.get("entity", "contact")
        name = params.arguments.get("name")
        page_map = {
            "organization": "organizations",
            "contact": "contacts",
            "opportunity": "opportunities",
            "quote": "quotes",
            "activity": "activities",
        }
        page = page_map.get(entity, "contacts")
        logger.info(
            "bob_action_create_dialog",
            entity=entity,
            name=name,
            page=page,
            session_id=session.session_id,
        )
        action: dict = {"type": "open_create_dialog", "entity": entity, "page": page}
        if name:
            action["name"] = name
        # Push action to frontend via server message
        if task_ref:
            from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
            server_msg = {"type": "bob_action", "action": action}
            await task_ref[0].queue_frame(RTVIServerMessageFrame(data=server_msg))
        result = {"status": "ok", "action": "open_create_dialog", "entity": entity, "page": page}
        if name:
            result["name"] = name
        await params.result_callback(result)

    llm.register_function("navigate_to", handle_navigate)
    llm.register_function("open_create_dialog", handle_create_dialog)

    # ── TTS (Orpheus on Groq) ────────────────────────────
    # Read user's saved voice preference from bob settings
    tts_voice = settings.groq_tts_voice  # default from config
    try:
        from app.presentation.routes.bob_settings_routes import _user_settings
        user_settings = _user_settings.get(user_id)
        if user_settings and user_settings.voice.voice:
            tts_voice = user_settings.voice.voice
            logger.info(
                "voice_using_user_setting",
                voice=tts_voice,
                user_id=user_id,
            )
    except Exception as e:
        logger.warning("voice_settings_lookup_failed", error=str(e))

    tts = GroqTTSService(
        api_key=settings.groq_api_key,
        voice_id=tts_voice,
        model_name=settings.groq_tts_model,
    )

    # ── LLM Context with system prompt ───────────────────
    messages = [
        {"role": "system", "content": BOB_VOICE_SYSTEM_PROMPT},
    ]

    # Inject any existing conversation history from text chat
    for msg in session.messages:
        messages.append(msg)

    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    # ── Think tag filter (Qwen3 chain-of-thought cleanup) ─
    import re
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
    from pipecat.frames.frames import TextFrame

    class ThinkTagFilter(FrameProcessor):
        """Strip <think>...</think> blocks from streaming LLM text.

        Robust approach: uses regex for complete blocks + state tracking
        for streaming where tags arrive in separate tokens.
        """

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._in_think = False
            self._buffer = ""

        async def process_frame(self, frame, direction: FrameDirection):
            await super().process_frame(frame, direction)

            if not isinstance(frame, TextFrame):
                await self.push_frame(frame, direction)
                return

            text = frame.text

            # If currently inside a think block, buffer until we see </think>
            if self._in_think:
                self._buffer += text
                if "</think>" in self._buffer:
                    # Extract everything after </think>
                    after = self._buffer.split("</think>", 1)[1]
                    self._in_think = False
                    self._buffer = ""
                    if after.strip():
                        await self.push_frame(TextFrame(text=after), direction)
                return

            # Check if this text contains <think> (possibly partial)
            if "<think>" in text:
                # Split on <think> - keep before, discard after (until </think>)
                before, after = text.split("<think>", 1)
                if "</think>" in after:
                    # Complete think block in one frame
                    remainder = after.split("</think>", 1)[1]
                    clean = before + remainder
                else:
                    # Open think block - enter buffering mode
                    self._in_think = True
                    self._buffer = after
                    clean = before

                if clean.strip():
                    await self.push_frame(TextFrame(text=clean), direction)
                return

            # Also catch the <think tag arriving as a partial token
            if "<think" in text and ">" not in text.split("<think", 1)[1]:
                # Partial <think tag - might be "<think" without ">"
                before = text.split("<think", 1)[0]
                self._in_think = True
                self._buffer = ""
                if before.strip():
                    await self.push_frame(TextFrame(text=before), direction)
                return

            # No think tags — pass through
            await self.push_frame(frame, direction)

    think_filter = ThinkTagFilter()

    # ── Pipeline ─────────────────────────────────────────
    pipeline = Pipeline(
        [
            transport.input(),          # WebSocket audio in
            stt,                        # Speech-to-text
            context_aggregator.user(),  # Aggregate user transcript
            llm,                        # LLM response
            think_filter,               # Strip <think> tags
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
