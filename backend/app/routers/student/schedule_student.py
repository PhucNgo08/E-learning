from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.student import schedule_service
from app.dependencies.auth import get_current_student
from app.config.template_config import get_template_by_path


router = APIRouter(
    prefix="/student/schedule",
    tags=["Student - Schedule"]
)


@router.get("/", response_class=HTMLResponse)
async def schedule_redirect():
    return RedirectResponse(url="/student/schedule/calendar", status_code=302)


@router.get("/calendar", response_class=HTMLResponse)
async def view_calendar(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    tpl = get_template_by_path(request.url.path)
    events = schedule_service.get_student_schedule(db, current_user.id)

    return tpl.TemplateResponse(
        "schedule/calendar.html",
        {
            "request": request,
            "events": events,
            "student": current_user,
            "page_title": "🗓️ Lịch học & Kiểm tra",
            "active_page": "schedule",
        },
    )


@router.get("/list", response_class=HTMLResponse)
async def view_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_student)
):
    tpl = get_template_by_path(request.url.path)
    schedules = schedule_service.get_schedule_list(db, current_user.id)

    return tpl.TemplateResponse(
        "schedule/list.html",
        {
            "request": request,
            "schedules": schedules,
            "student": current_user,
            "page_title": "📋 Lịch học dạng danh sách",
            "active_page": "schedule",
        },
    )