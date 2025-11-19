"""
==========================================================
🎓 ROUTER: Student - Discussion (FULL PRODUCTION 2025)
Xử lý đầy đủ chức năng thảo luận:
- List All / Search
- List theo khóa
- Tạo bài thảo luận
- Xem chi tiết + reply tree vô hạn
- Gửi reply nhiều cấp
- Like / Unlike
- Delete đệ quy
==========================================================
"""

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    Query
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from math import ceil
import traceback

# Template & DB config
from app.config.template_config import templates
from app.database.connection import get_db

# Services
from app.services.student import discussion_service
from app.services.course_service import is_student_enrolled

# Models
from app.models.course import Course
from app.models.discussion import Discussion


# ======================================================
# 📌 Router config
# ======================================================
router = APIRouter(
    prefix="/student/discussion",
    tags=["Student - Discussion"]
)


# ======================================================
# 🏠 1️⃣ LIST ALL (mọi khóa học, phân trang)
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_discussions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    try:
        discussions_all = discussion_service.get_all_discussions_all_courses(db)

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
        print("❌ [Discussion][ListAll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách thảo luận.</h4>", 500)


# ======================================================
# 🔍 1.1️⃣ SEARCH
# ======================================================
@router.get("/search", response_class=HTMLResponse)
async def search_discussions(
    request: Request,
    keyword: str = Query(""),
    db: Session = Depends(get_db)
):
    try:
        discussions = discussion_service.search_discussions(db, keyword)

        return templates["student"].TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "page_title": f"🔍 Tìm kiếm: {keyword}",
                "active_page": "discussion",
            }
        )

    except Exception as e:
        print("❌ [Discussion][Search] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi tìm kiếm.</h4>", 500)


# ======================================================
# 🆕 2️⃣ FORM TẠO BÀI THẢO LUẬN (toàn hệ thống)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
async def create_general_discussion(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse("/auth/login", 302)

    # Lấy danh sách khóa học mà học viên đã ghi danh
    courses = (
        db.query(Course)
        .join(Discussion, isouter=True)  # optional join → không lọc kết quả
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
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    if not content.strip():
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Nội dung không được để trống."},
            400
        )

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Khóa học không tồn tại."},
            404
        )

    if not is_student_enrolled(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ Bạn chưa đăng ký khóa học này."},
            403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())

        return RedirectResponse(
            url=f"/student/discussion/{course_id}",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        print("❌ [CreateGeneral] Lỗi:", e)
        return HTMLResponse("<h4>Lỗi tạo thảo luận.</h4>", 500)


# ======================================================
# 📘 3️⃣ LIST THEO KHÓA HỌC
# ======================================================
@router.get("/{course_id}", response_class=HTMLResponse)
async def list_discussions(
    request: Request,
    course_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "❌ Khóa học không tồn tại."}, 404
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


# ======================================================
# ✏️ 4️⃣ FORM TẠO BÀI THẢO LUẬN THEO KHÓA
# ======================================================
@router.get("/create/{course_id}", response_class=HTMLResponse)
async def create_discussion_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "❌ Khóa học không tồn tại."}, 404
        )

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "course": course,
            "page_title": "✏️ Tạo bài thảo luận",
        }
    )


# ======================================================
# 📨 5️⃣ POST TẠO BÀI
# ======================================================
@router.post("/create/{course_id}")
async def create_discussion(
    request: Request,
    course_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    if not content.strip():
        return RedirectResponse(f"/student/discussion/create/{course_id}", 303)

    if not is_student_enrolled(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "⚠️ Bạn chưa đăng ký khóa học này."}, 403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())
        return RedirectResponse(f"/student/discussion/{course_id}", 303)

    except Exception as e:
        db.rollback()
        print("❌ [CreateDiscussion] Lỗi:", e)
        return HTMLResponse("<h4>Lỗi tạo bài thảo luận.</h4>", 500)


# ======================================================
# 🔍 6️⃣ DETAIL VIEW + REPLY TREE
# ======================================================
@router.get("/detail/{discussion_id}", response_class=HTMLResponse)
async def discussion_detail(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    try:
        discussion, replies = discussion_service.get_discussion_with_replies(db, discussion_id)

        if not discussion:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài thảo luận."},
                404
            )

        user_id = request.session.get("user_id")
        if not is_student_enrolled(db, user_id, discussion.course_id):
            return templates["student"].TemplateResponse(
                "error.html", {"request": request, "message": "⚠️ Bạn không có quyền xem bài này."}, 403
            )

        return templates["student"].TemplateResponse(
            "discussion/detail.html",
            {
                "request": request,
                "discussion": discussion,
                "replies": replies,
                "page_title": "📄 Chi tiết thảo luận",
            }
        )

    except Exception as e:
        print("❌ [Detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải chi tiết.</h4>", 500)


# ======================================================
# 💬 7️⃣ POST REPLY
# ======================================================
@router.post("/reply/{discussion_id}")
async def post_reply(
    request: Request,
    discussion_id: str,
    content: str = Form(...),
    parent_id: str = Form(None),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    if not content.strip():
        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", 303)

    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        return HTMLResponse("<h4>Bài thảo luận không tồn tại.</h4>", 404)

    if not is_student_enrolled(db, user_id, discussion.course_id):
        return HTMLResponse("<h4>⚠️ Không có quyền.</h4>", 403)

    try:
        discussion_service.add_reply(
            db=db,
            discussion_id=discussion_id,
            user_id=user_id,
            content=content.strip(),
            parent_id=parent_id or discussion_id
        )

        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", 303)

    except Exception as e:
        db.rollback()
        print("❌ [Reply] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi gửi phản hồi.</h4>", 500)


# ======================================================
# 👍 8️⃣ LIKE / UNLIKE
# ======================================================
@router.post("/like/{discussion_id}")
async def like_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        discussion_service.toggle_like(db, discussion_id, user_id)
        return RedirectResponse(f"/student/discussion/detail/{discussion_id}", 303)

    except Exception as e:
        db.rollback()
        print("❌ [Like] Lỗi:", e)
        return HTMLResponse("<h4>Lỗi xử lý Like.</h4>", 500)


# ======================================================
# 🗑️ 9️⃣ DELETE
# ======================================================
@router.post("/delete/{discussion_id}")
async def delete_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        result = discussion_service.delete_discussion(db, discussion_id, user_id)

        if result.get("error"):
            return HTMLResponse("<h4>⚠️ Bạn không có quyền xóa bài này.</h4>", 403)

        return RedirectResponse("/student/discussion/", 303)

    except Exception as e:
        db.rollback()
        print("❌ [Delete] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xóa bài thảo luận.</h4>", 500)
