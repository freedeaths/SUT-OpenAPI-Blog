from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.post import PostStatus
from app.schemas.user import UserResponse

class PostBase(BaseModel):
    """文章基础模型"""
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

class PostCreate(PostBase):
    """创建文章请求模型"""
    pass

class PostUpdate(PostBase):
    """更新文章请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[PostStatus] = None

class PostResponse(PostBase):
    """文章响应模型"""
    id: str
    author_id: str
    status: PostStatus
    created_at: datetime
    updated_at: datetime
    likes_count: int
    dislikes_count: int
    views_count: int
    comments_count: int
    author: Optional[UserResponse] = None

    class Config:
        from_attributes = True
