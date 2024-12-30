from sqlalchemy import Column, String, Enum, DateTime, Integer
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime, UTC
from enum import Enum as PyEnum
import uuid

class PostStatus(str, PyEnum):
    """Post status"""
    DRAFT = "DRAFT"         # Draft, only visible to the author
    ACTIVE = "ACTIVE"       # Published, visible to everyone and can be commented
    MODIFYING = "MODIFYING" # Modifying, no new comments are allowed, existing comments are visible
    ARCHIVED = "ARCHIVED"   # Archived, visible to everyone but cannot be commented

class Post(Base):
    """Post model"""
    __tablename__ = "posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    author_id = Column(String, nullable=False)  
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    status = Column(Enum(PostStatus), nullable=False, default=PostStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    likes_count = Column(Integer, nullable=False, default=0)
    dislikes_count = Column(Integer, nullable=False, default=0)
    views_count = Column(Integer, nullable=False, default=0)
    comments_count = Column(Integer, nullable=False, default=0)
