# app/schemas/course.py

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class CourseBase(BaseModel):
    course_code: str
    course_name: str
    description: Optional[str] = None
    credit_hours: Optional[int] = 3

    course_type: Optional[str] = "mandatory"
    subject: Optional[str] = None
    grade_level: Optional[int] = None
    difficulty_level: Optional[str] = "beginner"

    semester: Optional[int] = None
    status: Optional[str] = "draft"
    enrollment_mode: Optional[str] = "auto"

    max_students: Optional[int] = 100
    current_students: Optional[int] = 0
    is_public: Optional[bool] = False

    price: Optional[float] = 0
    discount_percent: Optional[int] = 0

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None

    allow_assignments: Optional[bool] = True
    default_submission_type: Optional[str] = "individual"
    assignment_count: Optional[int] = 0


class CourseCreate(CourseBase):
    teacher_id: str
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None


class CourseUpdate(CourseBase):
    teacher_id: Optional[str] = None
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None


class CourseResponse(CourseBase):
    id: str
    teacher_id: Optional[str]
    academic_year_id: Optional[str]
    major_id: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True
