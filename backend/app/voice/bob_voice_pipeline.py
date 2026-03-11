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

# ── Orpheus TTS emotion tags (preserved by TTSTextCleaner) ──────
ORPHEUS_EMOTION_TAGS = {
    "laugh", "chuckle", "sigh", "gasp", "cough", "sniffle", "groan", "yawn",
}
ORPHEUS_VOCAL_DIRECTIONS = {
    # Original Orpheus directions
    "cheerful", "whisper", "excited", "sad", "angry", "calm", "surprised",
    # Extended from Groq Orpheus docs (v1-english)
    "dramatically", "professionally", "authoritatively",
    "singsong", "breathy", "gravelly whisper", "rapid babbling",
}

# ── Qwen3-TTS instruction map — tone × language → natural language directives ──
QWEN_INSTRUCTIONS_MAP: dict[tuple[str, str], str] = {
    ("fr-CA", "professional"): "Voix naturelle et chaleureuse, rythme québécois professionnel. Intonation vivante, légèrement enjouée.",
    ("fr-CA", "friendly"):     "Voix enjouée et accessible, comme un collègue sympathique de Montréal.",
    ("fr-CA", "formal"):       "Voix posée et formelle, registre soutenu, diction claire.",
    ("fr-CA", "casual"):       "Voix décontractée et naturelle, ton conversationnel québécois.",
    ("fr-FR", "professional"): "Voix claire et posée, accent neutre français. Ton professionnel soutenu.",
    ("fr-FR", "friendly"):     "Voix chaleureuse et naturelle, accent parisien accessible.",
    ("fr-FR", "formal"):       "Voix formelle et articulée, registre académique français.",
    ("fr-FR", "casual"):       "Voix naturelle et décontractée, accent français standard.",
    ("fr",    "professional"): "Voix française naturelle et expressive. Ton professionnel engageant.",
    ("fr",    "friendly"):     "Voix chaleureuse et accessible, ton amical et naturel.",
    ("es",    "professional"): "Voz natural y expresiva en español. Tono profesional y claro.",
    ("pt",    "professional"): "Voz natural e expressiva em português. Tom profissional.",
}
# Fallback si le (langue, tone) exact n'est pas dans la map
QWEN_INSTRUCTIONS_LANG_FALLBACK: dict[str, str] = {
    "fr-CA": "Voix naturelle, rythme québécois professionnel.",
    "fr-FR": "Voix claire, accent neutre français.",
    "fr":    "Voix française naturelle et expressive.",
    "es":    "Voz natural y expresiva en español.",
    "pt":    "Voz natural em português.",
}

# ── Qwen voice catalog with language/accent metadata ────────────
QWEN_VOICE_CATALOG: dict[str, dict] = {
    # ── Custom clone (voice cloning inline via ref_audio) ──────────────────
    "Rick":        {"gender": "male",   "accent": ["fr-CA", "fr-FR", "fr", "es", "pt"], "style": "custom"},

    # ── Féminines — chaleureuses / naturelles (idéales FR-CA) ─────────────
    "Cherry":      {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "friendly"},
    "Serena":      {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "friendly"},
    "Maia":        {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "professional"},
    "Mia":         {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "friendly"},
    "Vivian":      {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "casual"},
    "Momo":        {"gender": "female", "accent": ["fr-CA", "fr", "es", "pt"],          "style": "casual"},

    # ── Féminines — professionnelles / formelles (idéales FR-FR) ──────────
    "Jennifer":    {"gender": "female", "accent": ["fr-CA", "fr-FR", "fr", "es", "pt"], "style": "professional"},
    "Katerina":    {"gender": "female", "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Elias":       {"gender": "female", "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Bellona":     {"gender": "female", "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Bella":       {"gender": "female", "accent": ["fr-CA", "fr-FR", "fr", "es", "pt"], "style": "casual"},

    # ── Masculines — dynamiques / accessibles (idéales FR-CA) ─────────────
    "Ethan":       {"gender": "male",   "accent": ["fr-CA", "fr-FR", "fr", "es", "pt"], "style": "professional"},
    "Aiden":       {"gender": "male",   "accent": ["fr-CA", "fr", "es", "pt"],          "style": "casual"},
    "Mochi":       {"gender": "male",   "accent": ["fr-CA", "fr", "es", "pt"],          "style": "casual"},
    "Kai":         {"gender": "male",   "accent": ["fr-CA", "fr", "es", "pt"],          "style": "friendly"},
    "Moon":        {"gender": "male",   "accent": ["fr-CA", "fr", "es", "pt"],          "style": "professional"},

    # ── Masculines — formelles / expressives (idéales FR-FR) ──────────────
    "Ryan":        {"gender": "male",   "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Neil":        {"gender": "male",   "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Vincent":     {"gender": "male",   "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
    "Arthur":      {"gender": "male",   "accent": ["fr-CA", "fr-FR", "fr", "es", "pt"], "style": "friendly"},
    "Eldric Sage": {"gender": "male",   "accent": ["fr-FR", "fr", "es", "pt"],          "style": "formal"},
}


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

CRITICAL OUTPUT RULES — YOUR TEXT IS SPOKEN ALOUD:
- Your text is sent DIRECTLY to a text-to-speech engine and played aloud.
- ONLY output the words you want spoken. Nothing else.
- NEVER output internal reasoning, planning, commentary, or "thinking" text.
- NEVER write lines like "Let me think...", "I should use...", "Maybe add...", "ACTION:", etc.
- NEVER narrate what you're about to do — just DO it (call the tool) and confirm briefly.
- If you need to call a tool, call it silently and then say a short confirmation.

FORMATTING — ABSOLUTE PROHIBITION:
- NEVER use ANY markdown: no *, **, #, ##, -, bullet points, backticks, underscores.
- NEVER use numbered lists ("1. First...", "2. Second...").
- NEVER include URLs or links.
- NEVER use parenthetical asides like "(e.g., ...)", "(i.e., ...)".
- NEVER use ellipsis (...) or em-dashes (—).
- Write ONLY plain spoken English or French. Nothing that looks like text formatting.
- BAD: "Here are **three** things: 1. First... 2. Second..."
- GOOD: "There are three things. First, you can do this. Second, there's that."

EMOTION & EXPRESSIVENESS:
- You can use emotion tags to make your speech more natural and human.
- Available emotion tags (insert inline): <laugh>, <chuckle>, <sigh>, <gasp>, <cough>, <yawn>
- Available vocal directions (insert BEFORE a sentence):
  [cheerful], [whisper], [excited], [sad], [angry], [calm], [surprised],
  [dramatically], [professionally], [authoritatively], [singsong], [breathy]

- WHEN TO USE vocal directions:
  - After successful navigation or action   → [cheerful]
  - Delivering CRM data, stats, or reports  → [professionally]
  - Important notice or urgent alert        → [dramatically]
  - Empathy, user frustration, apology      → [calm]
  - Standard 1-sentence reply               → no tag (natural cadence is best)

- EXAMPLES:
  "<chuckle> That's a great question, let me look into that."
  "[cheerful] Done, I've opened the contacts page for you."
  "[professionally] You have fourteen open opportunities this quarter."
  "[calm] I understand, that can be frustrating. Let me help."

- Use MAXIMUM ONE direction or tag per response. Omit entirely for short replies.
- CRITICAL: Vocal directions are ONLY for English (Orpheus TTS). In French, do NOT use any tags or directions — Qwen TTS will read them aloud.

Communication style for VOICE:
- Keep responses SHORT (1-3 sentences max for voice)
- Be conversational and natural
- If a question needs a long answer, give the key point first, then offer to elaborate
- Use natural language fillers when appropriate ("Sure thing", "Let me check", etc.)

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
                    confidence=0.7,
                    start_secs=0.3,
                    stop_secs=0.4,
                    min_volume=0.6,
                ),
            ),
            vad_audio_passthrough=False,
            serializer=ProtobufFrameSerializer(
                params=ProtobufFrameSerializer.InputParams(ignore_rtvi_messages=False),
            ),
            session_timeout=settings.voice_max_session_minutes * 60,
        ),
    )

    # ── Resolve user settings early — needed for STT language + TTS provider ──
    from app.agents.bob_orchestrator import (
        resolve_user_settings, build_personality_directives,
        load_bcc_context,
    )
    from pipecat.transcriptions.language import Language

    user_settings = resolve_user_settings(user_id)
    user_language = user_settings.language or "auto"

    WHISPER_LANGUAGE_MAP = {
        "fr": Language.FR,
        "fr-FR": Language.FR_FR,
        "fr-CA": Language.FR_CA,
        "es": Language.ES,
        "pt": Language.PT,
        "en": Language.EN,
    }
    whisper_lang = WHISPER_LANGUAGE_MAP.get(user_language)

    # ── STT (Whisper on Groq) ────────────────────────────
    stt_kwargs: dict = {
        "api_key": settings.groq_api_key,
        "model": settings.groq_whisper_model,
    }
    if whisper_lang:
        stt_kwargs["language"] = whisper_lang
    stt = GroqSTTService(**stt_kwargs)

    # ── LLM (Llama 3.3 70B on Groq) ─────────────────────────
    from app.agents.bob_tools import load_tools_from_bcc
    from app.infrastructure.database import SessionLocal as _VoiceToolSession
    _vtool_db = _VoiceToolSession()
    try:
        tools = load_tools_from_bcc(_vtool_db, session.tenant_id)
    finally:
        _vtool_db.close()

    llm = GroqLLMService(
        api_key=settings.groq_api_key,
        model=settings.bob_model,
    )

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

    # ── TTS — pick provider by language (settings already resolved above) ──
    tts_voice = user_settings.voice or settings.groq_tts_voice
    tts_speed = user_settings.speed
    personality_directives = build_personality_directives(user_settings, for_voice=True)

    QWEN_TTS_LANGUAGES = {"fr", "fr-FR", "fr-CA", "es", "pt"}
    # Built-in voices + "Rick" (custom cloned via ref_audio inline)
    QWEN_VOICE_IDS = {
        "Cherry", "Ethan", "Jennifer", "Ryan", "Katerina", "Elias", "Rick",
    }
    use_qwen_tts = (
        user_language in QWEN_TTS_LANGUAGES
        and settings.dashscope_api_key
    )

    if use_qwen_tts:
        from app.voice.dashscope_tts import DashScopeTTSService

        # ── Sélection de la voix selon la langue, avec fallback Cherry ──
        valid_qwen_voices = [
            v for v, meta in QWEN_VOICE_CATALOG.items()
            if user_language in meta["accent"]
        ]
        if not valid_qwen_voices:
            valid_qwen_voices = list(QWEN_VOICE_CATALOG.keys())
        qwen_voice = tts_voice if tts_voice in valid_qwen_voices else valid_qwen_voices[0]

        # ── Instructions dynamiques : langue × tone ──────────────────
        user_tone = user_settings.tone or "professional"
        qwen_instructions = (
            QWEN_INSTRUCTIONS_MAP.get((user_language, user_tone))
            or QWEN_INSTRUCTIONS_LANG_FALLBACK.get(user_language, "")
        )

        # Rick = voice cloning via ref_audio. DashScope ne connaît pas "Rick"
        # comme voice ID natif — on passe Cherry + ref_audio pour le cloning.
        actual_dashscope_voice = qwen_voice
        ref_audio_path = ""
        if qwen_voice == "Rick":
            actual_dashscope_voice = "Ethan"  # base voice masculine → meilleur cloning
            import os
            # settings.rick_ref_audio_path peut être un path local (hors container)
            # → on vérifie d'abord que le fichier existe réellement
            _settings_path = settings.rick_ref_audio_path or ""
            if _settings_path and os.path.isfile(_settings_path):
                ref_audio_path = _settings_path
            else:
                # Fallback: chemin relatif au fichier actuel (valable dans le container)
                fallback = os.path.join(os.path.dirname(__file__), "rick_ref.wav")
                ref_audio_path = fallback if os.path.isfile(fallback) else ""
            logger.info(
                "rick_voice_ref_audio",
                path=ref_audio_path,
                exists=bool(ref_audio_path),
            )

        # Transcription exacte du ref_audio Rick (whisper-large-v3 via Groq)
        # Source: youtube.com/watch?v=jXSNfHCpRvI — 15s, voix seule sans musique
        RICK_REF_TEXT = (
            "Hey, salut! Tu te cherches présentement un métier? T'asseoir devant "
            "un ordinateur dans un bureau à longueur de journée, c'est peut-être "
            "pas nécessairement ton truc. Laisse-moi te faire découvrir un métier "
            "auquel t'avais peut-être pas pensé, mais honnê"
        )
        rick_ref_text = RICK_REF_TEXT if qwen_voice == "Rick" else ""

        tts = DashScopeTTSService(
            api_key=settings.dashscope_api_key,
            model=settings.dashscope_tts_model,
            voice=actual_dashscope_voice,
            language=user_language,
            instructions=qwen_instructions,
            ref_audio_path=ref_audio_path,
            ref_text=rick_ref_text,
            speed=tts_speed,
        )
        tts_model_name = settings.dashscope_tts_model
        tts_provider = "dashscope"
    else:
        qwen_voice = None  # non utilisé pour Orpheus
        qwen_instructions = ""  # non utilisé pour Orpheus
        tts = GroqTTSService(
            api_key=settings.groq_api_key,
            voice_id=tts_voice,
            model_name=settings.groq_tts_model,
            params=GroqTTSService.InputParams(speed=tts_speed),
        )
        tts_model_name = settings.groq_tts_model
        tts_provider = "groq"

    logger.info(
        "voice_using_user_settings",
        voice=tts_voice if tts_provider == "groq" else (qwen_voice if use_qwen_tts else tts_voice),
        speed=tts_speed,
        tone=user_settings.tone,
        language=user_language,
        tts_provider=tts_provider,
        tts_model=tts_model_name,
        user_id=user_id,
    )

    # ── TTS character counter — intercepts text frames going to TTS ──
    from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
    from pipecat.frames.frames import TextFrame

    class TTSCharacterCounter(FrameProcessor):
        """Counts characters of text frames sent to TTS for accurate billing."""

        def __init__(self, voice_session: VoiceSession):
            super().__init__(name="TTSCharacterCounter")
            self._session = voice_session

        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if isinstance(frame, TextFrame) and direction == FrameDirection.DOWNSTREAM:
                text = frame.text if hasattr(frame, "text") else ""
                self._session.tts_characters_total += len(text)
            await self.push_frame(frame, direction)

    tts_counter = TTSCharacterCounter(session)

    # ── BCC Context Injection — via orchestrator ─────────
    bcc_context = load_bcc_context(session.tenant_id)

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
    context.set_tool_choice("auto")
    context_aggregator = llm.create_context_aggregator(context)

    # ── TTS Text Transformers — clean text inside the TTS service ──────
    # Pipecat's TTS services have built-in text aggregation that bypasses
    # pipeline FrameProcessors. The correct approach is to register
    # text transformers directly on the TTS service.
    from app.voice.tts_text_cleaner import clean_text_for_tts

    import re as _re
    _THINK_STRIP = _re.compile(r"<think>.*?</think>\s*", flags=_re.DOTALL)
    _SLASH_THINK = _re.compile(r"/?(?:no_)?think\b", _re.IGNORECASE)

    _is_orpheus = not use_qwen_tts

    async def _tts_text_transform(text: str, aggregation_type=None) -> str:
        """Combined text transform: strip think tags + clean formatting."""
        # Strip <think> blocks
        text = _THINK_STRIP.sub("", text)
        text = _SLASH_THINK.sub("", text)
        # Clean markdown/formatting for TTS
        text = clean_text_for_tts(text, preserve_orpheus_tags=_is_orpheus)
        return text.strip()

    tts.add_text_transformer(_tts_text_transform)

    logger.info(
        "tts_text_transformer_registered",
        is_orpheus=_is_orpheus,
        provider=tts_provider,
    )

    # ── Pipeline ─────────────────────────────────────────
    pipeline = Pipeline(
        [
            transport.input(),          # WebSocket audio in
            stt,                        # Speech-to-text
            context_aggregator.user(),  # Aggregate user transcript
            llm,                        # LLM response
            tts_counter,               # Count characters for billing
            tts,                        # Text-to-speech (with text transforms)
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
        # ── Cancel pipeline immediately to stop VAD/STT infinite loop ──
        # Without this, VAD keeps firing every ~500ms with empty audio chunks
        # causing Groq STT 400 errors in an infinite loop.
        try:
            await task.cancel()
            logger.info("voice_pipeline_cancelled", session_id=session.session_id)
        except Exception as _cancel_err:
            logger.warning("voice_pipeline_cancel_failed", error=str(_cancel_err))

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
                    # TTS usage — real character count accumulated by TTSCharacterCounter
                    tts_chars = session.tts_characters_total
                    if tts_chars > 0:
                        _tracker.track_tts(
                            tenant_id=session.tenant_id,
                            user_id=user_id,
                            user_email=session.user_email,
                            model=tts_model_name,
                            characters=tts_chars,
                            trigger_source=TriggerSource.BOB_VOICE,
                            trigger_id=session.session_id,
                            correlation_id=session.session_id,
                            provider=tts_provider,
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
        tts_provider=tts_provider,
        tts_model=tts_model_name,
        tts_voice=tts_voice if tts_provider == "groq" else (qwen_voice if use_qwen_tts else tts_voice),
        language=user_language,
    )

    return task, runner
