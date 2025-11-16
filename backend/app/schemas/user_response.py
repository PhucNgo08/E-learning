# app/schemas/user_response.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None

    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    role: Optional[str] = None
    status: Optional[str] = None

    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None

    points: Optional[int] = 0
    level: Optional[int] = 1
    login_count: Optional[int] = 0
    total_learning_time: Optional[int] = 0

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
