from __future__ import annotations

from datetime import datetime
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.services.teacher import schedule_service


router = APIRouter(
    prefix="/teacher/schedule",
    tags=["Teacher - Schedule"],
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {"request": request}
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/schedule/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def list_schedule_week(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    schedule = schedule_service.get_teacher_schedule(db, teacher.id)

    return render_template(
        request,
        "schedule/list.html",
        {
            "teacher": teacher,
            "user": teacher,
            "schedule_days": schedule.get("days", []),
            "week_start": schedule.get("week_start", ""),
            "week_end": schedule.get("week_end", ""),
            "page_title": "Lịch dạy trong tuần",
            "active_page": "schedule",
            "now": datetime.now(),
        },
    )


@router.get("/calendar", response_class=HTMLResponse)
def view_calendar_month(
    request: Request,
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    current_month = month or datetime.now().month
    current_year = year or datetime.now().year

    lessons = schedule_service.get_teacher_schedule_month(
        db,
        teacher.id,
        month=current_month,
        year=current_year,
    )

    return render_template(
        request,
        "schedule/schedule.html",
        {
            "teacher": teacher,
            "user": teacher,
            "schedule_json": json.dumps(lessons, ensure_ascii=False),
            "month": current_month,
            "year": current_year,
            "page_title": "Lịch dạy theo tháng",
            "active_page": "schedule",
            "now": datetime.now(),
        },
    )
