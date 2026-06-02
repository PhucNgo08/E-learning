from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.services.student.learning_path_service import get_learning_path

router = APIRouter(prefix="/student/learning-path", tags=["Student - Learning Path"])


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/{course_id}", response_class=HTMLResponse)
async def learning_path_detail(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
):
    student_id = get_current_student_id(request)
    if not student_id:
        return RedirectResponse("/auth/login", status_code=302)

    data = get_learning_path(db, student_id, course_id)
    if data.get("status") == "forbidden":
        return HTMLResponse(data.get("message", "Bạn chưa có quyền xem lộ trình."), status_code=403)
    if data.get("status") != "success":
        return HTMLResponse(data.get("message", "Không thể tải lộ trình học."), status_code=404)

    return templates["student"].TemplateResponse(
        "learning_path/detail.html",
        {
            "request": request,
            **data,
            "page_title": "Gợi ý lộ trình học",
            "active_page": "learning_path",
        },
    )
