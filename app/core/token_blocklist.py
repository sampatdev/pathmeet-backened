from app.core.redis import redis_client

async def block_token(jti: str, expires_in_seconds: int):
    await redis_client.set(f"blocklist:{jti}", "true", ex=expires_in_seconds)

async def is_token_blocked(jti: str) -> bool:
    return await redis_client.exists(f"blocklist:{jti}") == 1