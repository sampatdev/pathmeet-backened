import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base

class LocationHistory(Base):
    __tablename__ = "location_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meetup_sessions.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)