import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.db.session import AsyncSessionLocal
from app.models import MeetupSession, SessionStatus


async def expire_stale_sessions(ctx):
    """Cancel any meetup session still 'pending' after 30 minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(MeetupSession)
            .where(
                MeetupSession.status == SessionStatus.pending,
                MeetupSession.created_at < cutoff,
            )
            .values(status=SessionStatus.cancelled)
        )
        await db.commit()
        print(f"Expired {result.rowcount} stale session(s)")


async def notify_friend_arrived(ctx, session_id: str, arriving_user_id: str):
    """Simulate a push notification. In production this would call FCM/APNs/etc."""
    print(f"[NOTIFY] User {arriving_user_id} is arriving at session {session_id} — sending push notification")