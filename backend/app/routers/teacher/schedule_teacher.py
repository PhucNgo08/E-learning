"""
==========================================================
📅 ROUTER: Teacher - Schedule Management
Quản lý lịch giảng dạy theo tuần và theo tháng cho giáo viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path
from app.services.teacher import schedule_service

router = APIRouter(
    prefix="/teacher/schedule",
    tags=["Teacher - Schedule"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/schedule/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def list_schedule_week(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher
    schedule = schedule_service.get_teacher_schedule(db, teacher.id)

    return render_template(
        request,
        "schedule/list.html",
        {
            "teacher": teacher,
            "schedule_days": schedule["days"],
            "week_start": schedule["week_start"],
            "week_end": schedule["week_end"],
            "page_title": "📅 Lịch dạy trong tuần",
            "now": datetime.now(),
        },
    )


@router.get("/calendar", response_class=HTMLResponse)
def view_calendar_month(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher

    lessons = schedule_service.get_teacher_schedule_month(
        db,
        teacher.id,
        month=datetime.now().month,
        year=datetime.now().year,
    )

    return render_template(
        request,
        "schedule/schedule.html",
        {
            "teacher": teacher,
            "schedule_json": json.dumps(lessons, ensure_ascii=False),
            "month": datetime.now().month,
            "year": datetime.now().year,
            "page_title": "🗓️ Lịch dạy theo tháng",
        },
    )