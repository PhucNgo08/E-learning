# app/schemas/enrollment.py

from pydantic import BaseModel
from typing import Optional

class EnrollmentBase(BaseModel):
    user_id: str
    class_id: str
    enrollment_status: str

class EnrollmentCreate(EnrollmentBase):
    applied_at: Optional[str] = None

class EnrollmentUpdate(EnrollmentBase):
    enrollment_status: Optional[str] = None

class EnrollmentResponse(EnrollmentBase):
    id: str

    class Config:
        from_attributes = True
