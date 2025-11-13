"""
==========================================================
💬 ROUTER: Admin - Discussion Management (v3.1 Synced)
Quản lý thảo luận trong hệ thống (CRUD + Template + Safe)
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
import traceback

# ✅ Nội bộ
from app.database.connection import get_db
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

# ✅ Models
from app.models.discussion import Discussion
from app.models.user import User
from app.models.course import Course

# ✅ Services
from app.services.admin.discussion_service import (
    get_all_discussions,
    delete_discussion,
)

# ======================================================
# ⚙️ Router
# ======================================================
router = APIRouter(
    prefix="/admin/discussion",
    tags=["Admin - Discussion Management"],
)


# ======================================================
# 📋 1️⃣ Danh sách thảo luận
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def list_discussions(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Hiển thị danh sách thảo luận"""
    try:
        tpl = get_template_by_path(request.url.path)

        # ✅ Lấy danh sách thảo luận, người dùng và khóa học
        discussions = get_all_discussions(db)
        user_map = {u.id: u.full_name for u in db.query(User).all()}
        course_map = {c.id: c.course_name for c in db.query(Course).all()}
        total = len(discussions)

        # ✅ Template path: không có 'admin/' prefix (theo chuẩn file_storage)
        return tpl.TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "user_map": user_map,
                "course_map": course_map,
                "total": total,
                "page_title": "💬 Quản lý Thảo luận",
                "active_page": "discussion",
            },
        )

    except Exception as e:
        print("❌ Lỗi khi load danh sách thảo luận:", e)
        traceback.print_exc()
        return HTMLResponse(
            f"<pre style='color:red; font-size:14px;'>{traceback.format_exc()}</pre>",
            status_code=500,
        )


# ======================================================
# 🗑️ 2️⃣ Xóa thảo luận
# ======================================================
@router.get("/delete/{discussion_id}", response_class=HTMLResponse)
def confirm_delete(
    discussion_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Xác nhận xóa thảo luận"""
    try:
        tpl = get_template_by_path(request.url.path)
        discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
        if not discussion:
            raise HTTPException(status_code=404, detail="Không tìm thấy thảo luận")

        user = db.query(User).filter(User.id == discussion.user_id).first()
        course = db.query(Course).filter(Course.id == discussion.course_id).first()

        return tpl.TemplateResponse(
            "discussion/delete.html",
            {
                "request": request,
                "discussion": discussion,
                "user": user,
                "course": course,
                "page_title": "🗑️ Xóa Thảo luận",
                "active_page": "discussion",
            },
        )

    except Exception as e:
        print("❌ Lỗi khi hiển thị trang xóa:", e)
        traceback.print_exc()
        return HTMLResponse(
            f"<pre style='color:red;'>{traceback.format_exc()}</pre>",
            status_code=500,
        )


@router.post("/delete/{discussion_id}")
def delete_action(
    discussion_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Xóa thảo luận (bao gồm cả reply con nếu có)"""
    try:
        deleted = delete_discussion(db, discussion_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Không thể xóa thảo luận")

        return RedirectResponse(url="/admin/discussion/list", status_code=303)

    except Exception as e:
        print("❌ Lỗi khi xóa thảo luận:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
