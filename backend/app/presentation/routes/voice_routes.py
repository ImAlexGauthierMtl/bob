"""Voice WebSocket routes — real-time voice endpoint for Bob.

Provides a WebSocket endpoint at /ws/bob/voice that accepts
audio streams and returns Bob's voice responses via Pipecat pipeline.
"""

import structlog

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import jwt

from app.config import settings
from app.voice.voice_session import voice_session_manager
from app.voice.bob_voice_pipeline import create_bob_voice_pipeline
from app.middleware.rate_limiter import rate_limiter

logger = structlog.get_logger(__name__)

router = APIRouter()


def _verify_ws_token(token: str) -> dict | None:
    """Verify JWT token from WebSocket query param.

    WebSockets can't use Authorization headers, so token
    is passed as a query parameter.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except Exception:
        return None


@router.websocket("/ws/bob/voice")
async def bob_voice_ws(websocket: WebSocket, token: str = ""):
    """WebSocket endpoint for real-time Bob voice conversation.

    Connection flow:
    1. Client connects with JWT token as query param: /ws/bob/voice?token=<jwt>
    2. Server authenticates and creates a VoiceSession
    3. Pipecat pipeline is built (STT → LLM → TTS)
    4. Audio streams bidirectionally until disconnect
    5. Session is cleaned up on disconnect

    Audio format:
    - Input: Raw PCM audio (16kHz, 16-bit, mono)
    - Output: PCM audio with WAV header (48kHz from Groq TTS)
    """
    # ── Auth ─────────────────────────────────────────────
    user = _verify_ws_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("voice_ws_auth_failed")
        return

    # ── Rate limit check ──────────────────────────────────
    try:
        rate_limiter.check_voice(user.get("sub", ""))
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("voice_ws_rate_limited", user=user.get("email"))
        return

    # ── Concurrency check ────────────────────────────────
    if not voice_session_manager.semaphore.locked():
        pass  # slots available
    else:
        await websocket.close(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason="Too many active voice sessions",
        )
        logger.warning(
            "voice_ws_concurrency_limit",
            user=user.get("email"),
            active=voice_session_manager.get_active_count(),
        )
        return

    # ── Accept connection ────────────────────────────────
    await websocket.accept()

    # ── Create session ───────────────────────────────────
    session = await voice_session_manager.create_session(
        user_id=user.get("sub", ""),
        tenant_id=user.get("tenant_id", ""),
        user_email=user.get("email", ""),
        max_duration_minutes=settings.voice_max_session_minutes,
    )

    logger.info(
        "voice_ws_connected",
        session_id=session.session_id,
        user=user.get("email"),
    )

    try:
        # ── Build and run pipeline ───────────────────────
        async with voice_session_manager.semaphore:
            task, runner = await create_bob_voice_pipeline(
                websocket=websocket,
                session=session,
                user_id=user.get("sub", ""),
            )
            await runner.run(task)

    except WebSocketDisconnect:
        logger.info(
            "voice_ws_disconnected",
            session_id=session.session_id,
            user=user.get("email"),
        )
    except Exception as e:
        logger.error(
            "voice_ws_error",
            session_id=session.session_id,
            error=str(e),
        )
    finally:
        voice_session_manager.close_session(session.session_id)
        logger.info(
            "voice_ws_cleanup",
            session_id=session.session_id,
            active_sessions=voice_session_manager.get_active_count(),
        )
