import json
from aiokafka import AIOKafkaProducer
from app.core.config import settings

kafka_producer: AIOKafkaProducer | None = None

async def start_kafka_producer():
    global kafka_producer
    kafka_producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await kafka_producer.start()
    print(">>> KAFKA PRODUCER STARTED SUCCESSFULLY")

async def stop_kafka_producer():
    if kafka_producer:
        await kafka_producer.stop()

async def publish_location_event(session_id: str, user_id: str, lat: float, lng: float):
    if kafka_producer is None:
        return  # producer not started yet, fail silently for now
    payload = json.dumps({"session_id": session_id, "user_id": user_id, "lat": lat, "lng": lng}).encode("utf-8")
    await kafka_producer.send_and_wait("location-updates", key=session_id.encode("utf-8"), value=payload)