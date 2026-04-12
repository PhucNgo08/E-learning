from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

from app.models.discussion import Discussion
from app.models.user import User
from app.models.course import Course

from app.services.admin.discussion_service import (
    get_all_discussions,
    delete_discussion,
)

router = APIRouter(
    prefix="/admin/discussion",
    tags=["Admin - Discussion Management"],
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "discussion",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def get_user_display_name(user) -> str:
    if not user:
        return "Không rõ"
    return (
        getattr(user, "full_name", None)
        or getattr(getattr(user, "user_profile", None), "full_name", None)
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or "Không rõ"
    )


def get_course_display_name(course) -> str:
    if not course:
        return "Không rõ"
    return getattr(course, "course_name", None) or getattr(course, "title", None) or "Không rõ"


@router.get("/list", response_class=HTMLResponse)
def list_discussions(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    del current_user

    try:
        discussions = get_all_discussions(db)
        users = db.query(User).all()
        courses = db.query(Course).all()

        user_map = {u.id: get_user_display_name(u) for u in users}
        course_map = {c.id: get_course_display_name(c) for c in courses}

        return render_template(
            request,
            "discussion/list.html",
            {
                "discussions": discussions,
                "user_map": user_map,
                "course_map": course_map,
                "total": len(discussions),
                "success": success,
                "error": error,
                "page_title": "💬 Quản lý Thảo luận",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi tải danh sách thảo luận: {str(e)}",
        ) from e


@router.get("/delete/{discussion_id}", response_class=HTMLResponse)
def confirm_delete(
    discussion_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    del current_user

    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Không tìm thấy thảo luận.")

    user = db.query(User).filter(User.id == discussion.user_id).first()
    course = db.query(Course).filter(Course.id == discussion.course_id).first()

    return render_template(
        request,
        "discussion/delete.html",
        {
            "discussion": discussion,
            "user": user,
            "course": course,
            "page_title": "🗑️ Xóa Thảo luận",
            "user_name": get_user_display_name(user),
            "course_name": get_course_display_name(course),
        },
    )


@router.post("/delete/{discussion_id}")
def delete_action(
    discussion_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    del current_user

    try:
        deleted = delete_discussion(db, discussion_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy thảo luận để xóa.")

        message = quote("Xóa thảo luận thành công.")
        return RedirectResponse(
            url=f"/admin/discussion/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except HTTPException:
        raise
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/discussion/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi xóa thảo luận: {str(e)}")
        return RedirectResponse(
            url=f"/admin/discussion/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )