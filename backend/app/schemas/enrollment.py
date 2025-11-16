# app/schemas/enrollment.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EnrollmentBase(BaseModel):
    user_id: str
    class_id: Optional[str] = None
    course_id: Optional[str] = None

    enrollment_type: Optional[str] = "official"
    enrollment_status: Optional[str] = "applied"

    applied_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    enrolled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    approved_by: Optional[str] = None

    final_grade: Optional[float] = None
    grade_letter: Optional[str] = None


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(EnrollmentBase):
    pass


class EnrollmentResponse(EnrollmentBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
