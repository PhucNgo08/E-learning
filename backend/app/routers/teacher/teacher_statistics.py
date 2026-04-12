from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.services.teacher import statistics_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/statistics",
    tags=["Teacher - Statistics"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "now": datetime.now(),
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_statistics_root():
    return RedirectResponse("/teacher/statistics/index", status_code=303)


@router.get("/index", response_class=HTMLResponse)
def teacher_statistics(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher = current_teacher

    try:
        data = statistics_service.get_teacher_statistics(db, teacher.id)
        return render_template(
            request,
            "statistics/index.html",
            {
                "teacher": teacher,
                "data": data,
                "page_title": "📊 Thống kê tổng quan",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể tải thống kê giáo viên: {e}")