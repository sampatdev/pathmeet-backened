import json
import uuid
from app.core.redis import redis_client

LOCATION_TTL_SECONDS = 3600  # 1 hour

def _key(session_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"location:{session_id}:{user_id}"

async def set_last_location(session_id: uuid.UUID, user_id: uuid.UUID, lat: float, lng: float):
    payload = json.dumps({"lat": lat, "lng": lng})
    await redis_client.set(_key(session_id, user_id), payload, ex=LOCATION_TTL_SECONDS)

async def get_last_location(session_id: uuid.UUID, user_id: uuid.UUID) -> dict | None:
    raw = await redis_client.get(_key(session_id, user_id))
    if raw is None:
        return None
    return json.loads(raw)