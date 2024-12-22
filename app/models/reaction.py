from datetime import datetime, UTC
import uuid
import enum
from sqlalchemy import Column, String, Enum as SQLEnum, DateTime

from app.db.database import Base

class ReactionType(str, enum.Enum):
    """Reaction type"""
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"

class TargetType(str, enum.Enum):
    """Target type"""
    POST = "post"
    COMMENT = "comment"
    REPLY = "reply"

class Reaction(Base):
    """Reaction model"""
    __tablename__ = "reactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(SQLEnum(TargetType), nullable=False)
    type = Column(SQLEnum(ReactionType), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
