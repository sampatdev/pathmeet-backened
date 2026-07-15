from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.meetup import MeetupSession, SessionParticipant
from app.schemas.meetup import MeetupSessionCreate, MeetupSessionResponse, AIStatusResponse
from app.core.location_cache import get_last_location
from app.core.ai_assistant import generate_status_update
from app.core.rate_limit import rate_limiter

# assumed average walking speed for a rough ETA estimate
AVERAGE_WALKING_SPEED_MPS = 1.4  # meters per second

def haversine_meters(lat1, lng1, lat2, lng2):
    import math
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    return R * 2 * math.asin(math.sqrt(a))

router = APIRouter(prefix="/meetups", tags=["meetups"])

@router.post("/", response_model=MeetupSessionResponse)
async def create_meetup(
    payload: MeetupSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.invitee_email))
    invitee = result.scalar_one_or_none()
    if not invitee:
        raise HTTPException(status_code=404, detail="Invitee not found")
    if invitee.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot invite yourself")

    session = MeetupSession(created_by=current_user.id)
    db.add(session)
    await db.flush()  # assigns session.id without committing yet

    db.add(SessionParticipant(session_id=session.id, user_id=current_user.id))
    db.add(SessionParticipant(session_id=session.id, user_id=invitee.id))

    await db.commit()
    await db.refresh(session)
    return session


@router.get("/{session_id}/location")
async def get_partner_location(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # confirm the requester is a participant
    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a participant of this session")

    # find the other participant
    other_result = await db.execute(
        select(SessionParticipant.user_id).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id != current_user.id,
        )
    )
    other_user_id = other_result.scalar_one_or_none()
    if not other_user_id:
        return {"location": None}

    location = await get_last_location(session_id, other_user_id)
    return {"user_id": str(other_user_id), "location": location}


@router.get(
    "/{session_id}/ai-status",
    response_model=AIStatusResponse,
    dependencies=[Depends(rate_limiter(10, 60))],
)
async def get_ai_status(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # confirm participant + find the other user (same pattern as the polling endpoint)
    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a participant of this session")

    other_result = await db.execute(
        select(SessionParticipant.user_id).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id != current_user.id,
        )
    )
    other_user_id = other_result.scalar_one_or_none()
    if not other_user_id:
        raise HTTPException(status_code=404, detail="No other participant found")

    my_loc = await get_last_location(session_id, current_user.id)
    their_loc = await get_last_location(session_id, other_user_id)

    if not my_loc or not their_loc:
        raise HTTPException(status_code=404, detail="Location data not available yet")

    distance = haversine_meters(my_loc["lat"], my_loc["lng"], their_loc["lat"], their_loc["lng"])
    eta_minutes = (distance / AVERAGE_WALKING_SPEED_MPS) / 60

    message = await generate_status_update(distance, eta_minutes)

    return AIStatusResponse(
        distance_meters=round(distance, 1),
        eta_minutes=round(eta_minutes, 1),
        status_message=message,
    )