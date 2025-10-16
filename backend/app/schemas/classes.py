# app/schemas/class.py

from pydantic import BaseModel
from typing import Optional

class ClassBase(BaseModel):
    class_code: str
    class_name: str
    status: str
    max_students: int

class ClassCreate(ClassBase):
    academic_year_id: str
    major_id: str
    start_date: Optional[str] = None  # Tùy chọn

class ClassUpdate(ClassBase):
    status: Optional[str] = None  # Cập nhật trạng thái lớp học

class ClassResponse(ClassBase):
    id: str

    class Config:
        from_attributes = True
