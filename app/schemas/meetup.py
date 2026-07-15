import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.meetup import SessionStatus

class MeetupSessionCreate(BaseModel):
    invitee_email: str

class MeetupSessionResponse(BaseModel):
    id: uuid.UUID
    created_by: uuid.UUID
    status: SessionStatus
    created_at: datetime

class AIStatusResponse(BaseModel):
    distance_meters: float
    eta_minutes: float | None
    status_message: str    

    class Config:
        from_attributes = True