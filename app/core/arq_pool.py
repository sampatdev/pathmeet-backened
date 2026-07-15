from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from app.core.config import settings

arq_pool: ArqRedis | None = None

async def start_arq_pool():
    global arq_pool
    arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

async def stop_arq_pool():
    if arq_pool:
        await arq_pool.close()