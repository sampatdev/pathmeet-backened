from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings as app_settings
from worker.tasks import expire_stale_sessions, notify_friend_arrived


class WorkerSettings:
    functions = [notify_friend_arrived]
    cron_jobs = [
        cron(expire_stale_sessions, minute=set(range(0, 60, 5))),  # every 5 minutes
    ]
    redis_settings = RedisSettings.from_dsn(app_settings.redis_url)