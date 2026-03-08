import asyncio
from unittest.mock import MagicMock

async def test():
    from app.voice.bob_voice_pipeline import create_bob_voice_pipeline
    from app.voice.voice_session import VoiceSession
    session = VoiceSession(user_id="test", tenant_id="test", user_email="test")
    ws = MagicMock()
    try:
        task, runner = await create_bob_voice_pipeline(websocket=ws, session=session, user_id="test")
        print("Pipeline built successfully!")
    except Exception as e:
        print(f"PIPELINE ERROR: {type(e).__name__}: {e}")

asyncio.run(test())
