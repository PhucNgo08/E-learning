from pydantic import BaseModel
from typing import Optional

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True  # Đổi từ 'orm_mode' thành 'from_attributes'
