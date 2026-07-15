import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.user import Base

class SessionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"

class MeetupSession(Base):
    __tablename__ = "meetup_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    participants: Mapped[list["SessionParticipant"]] = relationship(back_populates="session")

class SessionParticipant(Base):
    __tablename__ = "session_participants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetup_sessions.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    session: Mapped["MeetupSession"] = relationship(back_populates="participants")