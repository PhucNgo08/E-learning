# app/schemas/user_create.py

from pydantic import BaseModel
from typing import Optional
from datetime import date


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str

    # Academic Info
    mssv: Optional[str] = None
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None

    # Personal Info
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    # Role & Status
    role: Optional[str] = "student"
    status: Optional[str] = "active"


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

    mssv: Optional[str] = None
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None

    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    role: Optional[str] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]

    class Config:
        from_attributes = True
