# app/schemas/course.py

from pydantic import BaseModel
from typing import Optional

class CourseBase(BaseModel):
    course_code: str
    course_name: str
    credit_hours: int
    semester: int

class CourseCreate(CourseBase):
    teacher_id: str  # Dùng khi tạo khóa học mới

class CourseUpdate(CourseBase):
    semester: Optional[int] = None  # Dùng khi cập nhật khóa học

class CourseResponse(CourseBase):
    id: str

    class Config:
        from_attributes = True
