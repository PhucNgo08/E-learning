from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    submission_type: Optional[str] = "individual"
    allowed_file_types: Optional[str] = "pdf,docx,zip"
    max_files: Optional[int] = 5
    max_file_size_mb: Optional[int] = 50
    due_date: datetime
    allow_late_submission: bool = False
    late_penalty_percent: Optional[float] = 0
    total_points: Optional[float] = 10

class AssignmentCreate(AssignmentBase):
    course_id: str
    module_id: Optional[str] = None
    teacher_id: str

class AssignmentUpdate(AssignmentBase):
    id: str

class AssignmentResponse(AssignmentBase):
    id: str
    course_id: str
    module_id: Optional[str]
    teacher_id: str
    created_at: datetime

    class Config:
        orm_mode = True
