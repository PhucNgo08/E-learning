from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AIChatHistoryBase(BaseModel):
    message: str
    response: Optional[str]
    model_name: Optional[str]

class AIChatHistoryCreate(AIChatHistoryBase):
    user_id: str
    role: str = "user"

class AIChatHistoryOut(AIChatHistoryBase):
    id: str
    created_at: datetime
    role: str

    class Config:
        orm_mode = True
