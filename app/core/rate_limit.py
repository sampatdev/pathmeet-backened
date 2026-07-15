from fastapi import Request, HTTPException, status
from app.core.redis import redis_client

def rate_limiter(max_requests: int, window_seconds: int):
    async def limiter(request: Request):
        client_ip = request.client.host
        key = f"ratelimit:{request.url.path}:{client_ip}"

        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_seconds)

        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please try again later.",
            )

    return limiter