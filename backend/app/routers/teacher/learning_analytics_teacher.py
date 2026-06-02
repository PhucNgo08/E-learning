from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.services.teacher.learning_analytics_service import (
    get_course_learning_analytics,
    get_teacher_courses_overview,
)

router = APIRouter(
    prefix="/teacher/analytics", 
    tags=["Teacher - Learning Analytics"]
)


@router.get("/", response_class=HTMLResponse)
def analytics_index(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    data = get_teacher_courses_overview(db, current_teacher.id)
    return templates["teacher"].TemplateResponse(
        "analytics/index.html",
        {
            "request": request,
            "teacher": current_teacher,
            "data": data,
            "page_title": "Phân tích học tập",
            "active_page": "analytics",
        },
    )


@router.get("/course/{course_id}", response_class=HTMLResponse)
def analytics_course_detail(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    data = get_course_learning_analytics(db, current_teacher.id, course_id)
    if data.get("status") != "success":
        return HTMLResponse(data.get("message", "Không thể tải dashboard."), status_code=403)

    return templates["teacher"].TemplateResponse(
        "analytics/course_detail.html",
        {
            "request": request,
            "teacher": current_teacher,
            **data,
            "page_title": "Dashboard phân tích học tập",
            "active_page": "analytics",
        },
    )
