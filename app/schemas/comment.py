from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from app.models.comment import CommentStatus

class CommentBase(BaseModel):
    """评论基础模型"""
    content: str = Field(..., description="评论内容")

class CommentCreate(CommentBase):
    """创建评论请求模型"""
    pass

class CommentUpdate(BaseModel):
    """更新评论请求模型"""
    content: Optional[str] = Field(None, description="评论内容")

class CommentResponse(CommentBase):
    """评论响应模型"""
    id: str = Field(..., description="评论ID")
    post_id: str = Field(..., description="文章ID")
    author_id: str = Field(..., description="作者ID")
    status: CommentStatus = Field(..., description="评论状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    likes_count: int = Field(default=0, description="点赞数")
    dislikes_count: int = Field(default=0, description="点踩数")

    class Config:
        from_attributes = True
