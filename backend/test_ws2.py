import asyncio
from unittest.mock import MagicMock
from app.presentation.routes.voice_routes import bob_voice_ws

async def test():
    class MockWebsocket:
        def __init__(self):
            self.closed = False
        async def close(self, code=1000, reason=""):
            print(f"WS Closed! {code=} {reason=}")
            self.closed = True
        async def accept(self):
            print("WS Accepted!")

    ws = MockWebsocket()
    try:
        from app.config import settings
        from jose import jwt
        token = jwt.encode({"sub": "user_123", "email": "test@croo.com", "tenant_id": "tenant_123", "type": "access"}, settings.secret_key, algorithm=settings.jwt_algorithm)
        print("Calling route...")
        await bob_voice_ws(ws, token=token)
        print("Route finished gracefully")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
