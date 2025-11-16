from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AIChatHistoryBase(BaseModel):
    message: str
    response: Optional[str] = None
    model_name: Optional[str] = None


class AIChatHistoryCreate(AIChatHistoryBase):
    user_id: str
    role: str = "user"   # user hoặc assistant


class AIChatHistoryOut(AIChatHistoryBase):
    id: str
    user_id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True
