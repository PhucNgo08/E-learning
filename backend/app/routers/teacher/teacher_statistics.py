from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.services.teacher import statistics_service

router = APIRouter(prefix="/teacher/statistics", tags=["Teacher - Statistics"])


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "now": datetime.now(),
        "active_page": "statistics",
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/", include_in_schema=False)
def redirect_statistics_root():
    return RedirectResponse("/teacher/statistics/index", status_code=303)


@router.get("/index", response_class=HTMLResponse)
def teacher_statistics_index(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        data = statistics_service.get_teacher_statistics(db, current_teacher.id)
        return render_template(
            request,
            "statistics/index.html",
            {
                "teacher": current_teacher,
                "data": data,
                "page_title": "📊 Thống kê tổng quan",
                "active_page": "statistics",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Không thể tải thống kê giáo viên: {exc}")


@router.get("/progress", response_class=HTMLResponse)
def teacher_student_progress(
    request: Request,
    course_id: str | None = None,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    data = statistics_service.get_course_student_progress(db, current_teacher.id, course_id)
    return render_template(
        request,
        "statistics/progress.html",
        {
            **data,
            "teacher": current_teacher,
            "page_title": "Tiến độ học viên",
            "active_page": "student_progress",
        },
    )


@router.get("/progress/student/{student_id}", response_class=HTMLResponse)
def teacher_student_progress_detail(
    student_id: str,
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    data = statistics_service.get_student_progress_detail(db, current_teacher.id, course_id, student_id)
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy học viên hoặc bạn không có quyền xem khóa học này.")

    return render_template(
        request,
        "statistics/student_progress_detail.html",
        {
            **data,
            "teacher": current_teacher,
            "page_title": "Chi tiết tiến độ học viên",
            "active_page": "student_progress",
        },
    )
