from fastapi import FastAPI
from app.routers import auth, meetup
from fastapi import WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError
import uuid
from sqlalchemy import select
from contextlib import asynccontextmanager
import math

from app.core.connection_manager import manager
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.meetup import SessionParticipant
from app.core.location_cache import set_last_location, get_last_location
from app.core.kafka_producer import publish_location_event, start_kafka_producer, stop_kafka_producer
import app.core.arq_pool as arq_pool_module
from app.core.arq_pool import start_arq_pool, stop_arq_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_kafka_producer()
    await start_arq_pool()
    yield
    await stop_kafka_producer()
    await stop_arq_pool()


app = FastAPI(lifespan=lifespan)

app.include_router(auth.router)
app.include_router(meetup.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print("Client disconnected")

# @app.websocket("/ws/meetup/{session_id}")
# async def meetup_websocket(websocket: WebSocket, session_id: uuid.UUID, token: str = Query(...)):
#     # Verify the token manually (can't use Depends() with WebSockets the same way)
#     try:
#         payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
#         user_id = uuid.UUID(payload.get("sub"))
#     except (JWTError, ValueError, TypeError):
#         await websocket.close(code=1008)  # policy violation
#         return

#     # Verify this user is actually a participant of this session
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(
#             select(SessionParticipant).where(
#                 SessionParticipant.session_id == session_id,
#                 SessionParticipant.user_id == user_id,
#             )
#         )
#         participant = result.scalar_one_or_none()
#         if not participant:
#             await websocket.close(code=1008)
#             return

#     await manager.connect(session_id, user_id, websocket)
#     try:
#         while True:
#             data = await websocket.receive_json()
#             # data expected: {"lat": ..., "lng": ...}
#             await manager.send_to_session(
#                 session_id,
#                 sender_id=user_id,
#                 message={"user_id": str(user_id), "lat": data["lat"], "lng": data["lng"]},
#             )
#     except WebSocketDisconnect:
#         manager.disconnect(session_id, user_id)


@app.websocket("/ws/meetup/{session_id}")
async def meetup_websocket(websocket: WebSocket, session_id: uuid.UUID, token: str = Query(...)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SessionParticipant).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id == user_id,
            )
        )
        if not result.scalar_one_or_none():
            await websocket.close(code=1008)
            return

        # find the other participant while we still have a db session open
        other_result = await db.execute(
            select(SessionParticipant.user_id).where(
                SessionParticipant.session_id == session_id,
                SessionParticipant.user_id != user_id,
            )
        )
        other_user_id = other_result.scalar_one_or_none()

    await manager.connect(session_id, user_id, websocket)

    # send the other participant's last known location immediately, if we have one cached
    if other_user_id:
        last_loc = await get_last_location(session_id, other_user_id)
        if last_loc:
            await websocket.send_json({
                "user_id": str(other_user_id),
                "lat": last_loc["lat"],
                "lng": last_loc["lng"],
            })

    try:
        while True:
            data = await websocket.receive_json()
            await set_last_location(session_id, user_id, data["lat"], data["lng"])
            await publish_location_event(str(session_id), str(user_id), data["lat"], data["lng"])
            await manager.send_to_session(
                session_id,
                sender_id=user_id,
                message={"user_id": str(user_id), "lat": data["lat"], "lng": data["lng"]},
            )

            if other_user_id:
                other_loc = await get_last_location(session_id, other_user_id)
                if other_loc:
                    distance = haversine_meters(data["lat"], data["lng"], other_loc["lat"], other_loc["lng"])
                    if distance < 200 and arq_pool_module.arq_pool:
                        await arq_pool_module.arq_pool.enqueue_job("notify_friend_arrived", str(session_id), str(user_id))
                    
    except (WebSocketDisconnect, RuntimeError):
        manager.disconnect(session_id, user_id)

def haversine_meters(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    return R * 2 * math.asin(math.sqrt(a))        