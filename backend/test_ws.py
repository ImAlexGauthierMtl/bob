import asyncio
from datetime import timedelta
from jose import jwt
from app.config import settings

def create_token():
    payload = {
        "sub": "user_123",
        "email": "test@croo.com",
        "tenant_id": "tenant_123",
        "type": "access"
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

async def test():
    import websockets
    token = create_token()
    uri = f"ws://127.0.0.1:8555/ws/bob/voice?token={token}"
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as ws:
            print("Connected! Waiting 5 seconds...")
            await asyncio.sleep(5)
            print("Still connected!")
    except Exception as e:
        print(f"WS Exception: {type(e).__name__}: {e}")

asyncio.run(test())
