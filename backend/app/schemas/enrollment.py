from pydantic import BaseModel, model_validator
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

    @model_validator(mode="after")
    def validate_class_or_course(self):
        if not self.class_id and not self.course_id:
            raise ValueError("Phải có class_id hoặc course_id")
        return self


class EnrollmentCreate(EnrollmentBase):
    pass


class EnrollmentUpdate(BaseModel):
    class_id: Optional[str] = None
    course_id: Optional[str] = None

    enrollment_type: Optional[str] = None
    enrollment_status: Optional[str] = None

    applied_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    enrolled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    approved_by: Optional[str] = None
    final_grade: Optional[float] = None
    grade_letter: Optional[str] = None

    @model_validator(mode="after")
    def validate_class_or_course(self):
        if self.class_id is None and self.course_id is None:
            return self
        if not self.class_id and not self.course_id:
            raise ValueError("Nếu cập nhật liên quan enrollment target thì phải có class_id hoặc course_id")
        return self


class EnrollmentResponse(BaseModel):
    id: str
    user_id: str
    class_id: Optional[str] = None
    course_id: Optional[str] = None

    enrollment_type: Optional[str] = None
    enrollment_status: Optional[str] = None

    applied_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    enrolled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    approved_by: Optional[str] = None
    final_grade: Optional[float] = None
    grade_letter: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True