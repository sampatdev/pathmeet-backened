import asyncio
import json
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import LocationHistory


async def consume():
    consumer = AIOKafkaConsumer(
        "location-updates",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="location-history-writer",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    print("Location history consumer started, listening...")

    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                session_id = data["session_id"]
                user_id = data["user_id"]
                lat = data["lat"]
                lng = data["lng"]
            except (KeyError, json.JSONDecodeError) as e:
                print(f"Skipping malformed message at offset {msg.offset}: {e}")
                continue

            print(f"Writing to Postgres: {data}")

            async with AsyncSessionLocal() as db:
                entry = LocationHistory(
                    session_id=uuid.UUID(session_id),
                    user_id=uuid.UUID(user_id),
                    lat=lat,
                    lng=lng,
                    recorded_at=datetime.now(timezone.utc),
                )
                db.add(entry)
                await db.commit()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(consume())