from datetime import datetime
from pydantic import BaseModel, Field

from app.models.reaction import ReactionType, TargetType

class ReactionBase(BaseModel):
    """反应基础模型"""
    type: ReactionType = Field(..., description="反应类型")

class ReactionCreate(ReactionBase):
    """创建反应请求模型"""
    pass

class ReactionResponse(ReactionBase):
    """反应响应模型"""
    id: str = Field(..., description="反应ID")
    user_id: str = Field(..., description="用户ID")
    target_id: str = Field(..., description="目标ID")
    target_type: TargetType = Field(..., description="目标类型")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
