"""
==========================================================
🎓 ROUTER: Student - Discussion (Enrollment-based Access)
==========================================================
"""

from math import ceil
import logging
import traceback

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.models.course import Course
from app.models.discussion import Discussion
from app.services.common.course_access_service import (
    get_accessible_course_ids,
    has_course_access,
)
from app.services.student import discussion_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/student/discussion",
    tags=["Student - Discussion"]
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


def can_access_course(db: Session, user_id: str, course_id: str) -> bool:
    return has_course_access(db, user_id, course_id)


@router.get("/", response_class=HTMLResponse)
async def all_discussions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    try:
        user_id = get_current_student_id(request)
        if not user_id:
            return RedirectResponse("/auth/login", status_code=302)

        accessible_ids = get_accessible_course_ids(db, user_id)
        discussions_all = discussion_service.get_all_discussions_all_courses(db)
        discussions_all = [d for d in discussions_all if d.course_id in accessible_ids]

        total = len(discussions_all)
        start, end = (page - 1) * limit, page * limit
        discussions = discussions_all[start:end]
        total_pages = ceil(total / limit) if total else 1

        return templates["student"].TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "page": page,
                "total_pages": total_pages,
                "page_title": "💬 Tất cả thảo luận",
                "active_page": "discussion",
            }
        )

    except Exception as e:
        logger.exception("❌ [Discussion][ListAll] Lỗi: %s", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách thảo luận.</h4>", status_code=500)


@router.get("/search", response_class=HTMLResponse)
async def search_discussions(
    request: Request,
    keyword: str = Query(""),
    db: Session = Depends(get_db)
):
    try:
        user_id = get_current_student_id(request)
        if not user_id:
            return RedirectResponse("/auth/login", status_code=302)

        accessible_ids = get_accessible_course_ids(db, user_id)
        discussions = discussion_service.search_discussions(db, keyword)
        discussions = [d for d in discussions if d.course_id in accessible_ids]

        return templates["student"].TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "page": 1,
                "total_pages": 1,
                "keyword": keyword,
                "page_title": f"🔍 Tìm kiếm: {keyword}",
                "active_page": "discussion",
            }
        )

    except Exception as e:
        logger.exception("❌ [Discussion][Search] Lỗi: %s", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi tìm kiếm.</h4>", status_code=500)


@router.get("/create", response_class=HTMLResponse)
async def create_general_discussion(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    course_ids = get_accessible_course_ids(db, user_id)
    courses = []
    if course_ids:
        courses = (
            db.query(Course)
            .filter(Course.id.in_(course_ids))
            .order_by(Course.course_name.asc())
            .all()
        )

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "courses": courses,
            "page_title": "✏️ Tạo bài thảo luận",
            "active_page": "discussion",
        }
    )


@router.post("/create")
async def create_general_discussion_post(
    request: Request,
    course_id: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    if not content.strip():
        return templates["student"].TemplateResponse(
            "discussion/create_post.html",
            {
                "request": request,
                "courses": (
                    db.query(Course)
                    .filter(Course.id.in_(get_accessible_course_ids(db, user_id)))
                    .order_by(Course.course_name.asc())
                    .all()
                ),
                "error": "⚠️ Nội dung không được để trống.",
                "old_course_id": course_id,
                "old_content": content,
                "page_title": "✏️ Tạo bài thảo luận",
                "active_page": "discussion",
            },
            status_code=400
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Khóa học không tồn tại."},
            status_code=404
        )

    if not can_access_course(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Bạn chưa tham gia khóa học này."},
            status_code=403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())
        return RedirectResponse(url=f"/student/discussion/{course_id}", status_code=303)

    except Exception as e:
        db.rollback()
        logger.exception("❌ [CreateGeneral] Lỗi: %s", e)
        return HTMLResponse("<h4>Lỗi tạo thảo luận.</h4>", status_code=500)


@router.get("/create/{course_id}", response_class=HTMLResponse)
async def create_discussion_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Khóa học không tồn tại."},
            status_code=404
        )

    if not can_access_course(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Bạn chưa tham gia khóa học này."},
            status_code=403
        )

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "course": course,
            "page_title": "✏️ Tạo bài thảo luận",
            "active_page": "discussion",
        }
    )


@router.post("/create/{course_id}")
async def create_discussion(
    request: Request,
    course_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    if not content.strip():
        course = db.query(Course).filter(Course.id == course_id).first()
        return templates["student"].TemplateResponse(
            "discussion/create_post.html",
            {
                "request": request,
                "course": course,
                "error": "⚠️ Nội dung không được để trống.",
                "old_content": content,
                "page_title": "✏️ Tạo bài thảo luận",
                "active_page": "discussion",
            },
            status_code=400
        )

    if not can_access_course(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Bạn chưa tham gia khóa học này."},
            status_code=403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())
        return RedirectResponse(f"/student/discussion/{course_id}", status_code=303)

    except Exception as e:
        db.rollback()
        logger.exception("❌ [CreateDiscussion] Lỗi: %s", e)
        return HTMLResponse("<h4>Lỗi tạo bài thảo luận.</h4>", status_code=500)


@router.get("/detail/{discussion_id}", response_class=HTMLResponse)
async def discussion_detail(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    try:
        user_id = get_current_student_id(request)
        if not user_id:
            return RedirectResponse("/auth/login", status_code=302)

        discussion, replies = discussion_service.get_discussion_with_replies(db, discussion_id)
        if not discussion:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài thảo luận."},
                status_code=404
            )

        if not can_access_course(db, user_id, discussion.course_id):
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xem bài này."},
                status_code=403
            )

        return templates["student"].TemplateResponse(
            "discussion/detail.html",
            {
                "request": request,
                "discussion": discussion,
                "replies": replies,
                "page_title": "📄 Chi tiết thảo luận",
                "active_page": "discussion",
            }
        )

    except Exception as e:
        logger.exception("❌ [Detail] Lỗi: %s", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải chi tiết.</h4>", status_code=500)


@router.get("/{course_id}", response_class=HTMLResponse)
async def list_discussions(
    request: Request,
    course_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Khóa học không tồn tại."},
            status_code=404
        )

    if not can_access_course(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Bạn chưa tham gia khóa học này."},
            status_code=403
        )

    discussions_all = discussion_service.get_all_discussions(db, course_id)
    total = len(discussions_all)
    start, end = (page - 1) * limit, page * limit
    discussions = discussions_all[start:end]
    total_pages = ceil(total / limit) if total else 1

    return templates["student"].TemplateResponse(
        "discussion/list.html",
        {
            "request": request,
            "course": course,
            "discussions": discussions,
            "page": page,
            "total_pages": total_pages,
            "page_title": f"📘 Thảo luận – {course.course_name}",
            "active_page": "discussion",
        }
    )


@router.post("/reply/{discussion_id}")
async def post_reply(
    request: Request,
    discussion_id: str,
    content: str = Form(...),
    parent_id: str = Form(None),
    db: Session = Depends(get_db)
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    if not content.strip():
        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", status_code=303)

    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return HTMLResponse("<h4>Bài thảo luận không tồn tại.</h4>", status_code=404)

    if not can_access_course(db, user_id, discussion.course_id):
        return HTMLResponse("<h4>⚠️ Không có quyền.</h4>", status_code=403)

    try:
        discussion_service.add_reply(
            db=db,
            discussion_id=discussion_id,
            user_id=user_id,
            content=content.strip(),
            parent_id=parent_id or discussion_id
        )
        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", status_code=303)

    except Exception as e:
        db.rollback()
        logger.exception("❌ [Reply] Lỗi: %s", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi gửi phản hồi.</h4>", status_code=500)


@router.post("/like/{discussion_id}")
async def like_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return HTMLResponse("<h4>Bài thảo luận không tồn tại.</h4>", status_code=404)

    if not can_access_course(db, user_id, discussion.course_id):
        return HTMLResponse("<h4>⚠️ Không có quyền.</h4>", status_code=403)

    try:
        discussion_service.toggle_like(db, discussion_id, user_id)
        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", status_code=303)

    except Exception as e:
        db.rollback()
        logger.exception("❌ [Like] Lỗi: %s", e)
        return HTMLResponse("<h4>Lỗi xử lý Like.</h4>", status_code=500)


@router.post("/delete/{discussion_id}")
async def delete_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=302)

    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return HTMLResponse("<h4>Bài thảo luận không tồn tại.</h4>", status_code=404)

    try:
        result = discussion_service.delete_discussion(db, discussion_id, user_id)

        if result.get("error"):
            return HTMLResponse("<h4>⚠️ Bạn không có quyền xóa bài này.</h4>", status_code=403)

        return RedirectResponse(f"/student/discussion/{discussion.course_id}", status_code=303)

    except Exception as e:
        db.rollback()
        logger.exception("❌ [Delete] Lỗi: %s", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xóa bài thảo luận.</h4>", status_code=500)