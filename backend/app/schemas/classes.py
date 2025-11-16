# app/schemas/classes.py

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ClassBase(BaseModel):
    class_code: str
    class_name: str
    class_type: Optional[str] = "official"
    grade_level: Optional[int] = None

    max_students: Optional[int] = 50
    current_students: Optional[int] = 0

    status: Optional[str] = "planning"

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    enrollment_start: Optional[date] = None
    enrollment_end: Optional[date] = None


class ClassCreate(ClassBase):
    academic_year_id: str
    major_id: str
    homeroom_teacher_id: Optional[str] = None


class ClassUpdate(ClassBase):
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None
    homeroom_teacher_id: Optional[str] = None


class ClassResponse(ClassBase):
    id: str
    academic_year_id: Optional[str]
    major_id: Optional[str]
    homeroom_teacher_id: Optional[str]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
