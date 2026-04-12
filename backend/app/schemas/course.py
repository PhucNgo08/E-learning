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
    is_public: Optional[bool] = False

    price: Optional[float] = 0
    discount_percent: Optional[int] = 0

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None

    allow_assignments: Optional[bool] = True
    default_submission_type: Optional[str] = "individual"


class CourseCreate(CourseBase):
    teacher_id: str
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None


class CourseUpdate(BaseModel):
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    description: Optional[str] = None
    credit_hours: Optional[int] = None

    course_type: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[int] = None
    difficulty_level: Optional[str] = None

    teacher_id: Optional[str] = None
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None

    semester: Optional[int] = None
    status: Optional[str] = None
    enrollment_mode: Optional[str] = None

    max_students: Optional[int] = None
    is_public: Optional[bool] = None

    price: Optional[float] = None
    discount_percent: Optional[int] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None

    allow_assignments: Optional[bool] = None
    default_submission_type: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    course_code: str
    course_name: str
    description: Optional[str] = None
    credit_hours: Optional[int] = None

    course_type: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[int] = None
    difficulty_level: Optional[str] = None

    teacher_id: Optional[str] = None
    academic_year_id: Optional[str] = None
    major_id: Optional[str] = None

    semester: Optional[int] = None
    status: Optional[str] = None
    enrollment_mode: Optional[str] = None

    max_students: Optional[int] = None
    current_students: Optional[int] = None
    is_public: Optional[bool] = None

    price: Optional[float] = None
    discount_percent: Optional[int] = None

    start_date: Optional[date] = None
    end_date: Optional[date] = None

    thumbnail_url: Optional[str] = None
    prerequisites: Optional[str] = None

    allow_assignments: Optional[bool] = None
    default_submission_type: Optional[str] = None
    assignment_count: Optional[int] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True