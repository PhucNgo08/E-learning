from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.dependencies.auth import get_current_student
from app.services.student.todo_service import get_student_todo

router = APIRouter(prefix="/student", tags=["Student - Todo"])


@router.get("/todo", response_class=HTMLResponse)
def student_todo_page(
    request: Request,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    todo = get_student_todo(db, current_student.id)
    return templates["student"].TemplateResponse(
        "todo/index.html",
        {
            "request": request,
            "user": current_student,
            "todo": todo,
            "page_title": "Việc cần làm",
            "active_page": "todo",
            "now": datetime.utcnow() + timedelta(hours=7),
        },
    )
