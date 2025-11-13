"""
==========================================================
🎓 ROUTER: Student - Discussion
Xử lý đầy đủ chức năng thảo luận học viên trong khóa học
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

# ✅ Import cấu hình template & DB
from app.config.template_config import templates
from app.database.connection import get_db
from app.services.student import discussion_service
from app.services.course_service import is_student_enrolled

# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/discussion",
    tags=["Student - Discussion"]
)

# ======================================================
# 🏠 1️⃣ Danh sách thảo luận (mọi khóa học, có phân trang)
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_discussions(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    """Hiển thị tất cả bài thảo luận của mọi khóa học (phân trang)."""
    try:
        discussions_all = discussion_service.get_all_discussions_all_courses(db)
        total = len(discussions_all)
        start, end = (page - 1) * limit, page * limit
        discussions = discussions_all[start:end]
        total_pages = ceil(total / limit)

        return templates["student"].TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "page": page,
                "total_pages": total_pages,
                "page_title": "💬 Tất cả thảo luận",
                "active_page": "discussion",
            },
        )

    except Exception as e:
        print("❌ [Discussion][ListAll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách thảo luận.</h4>", status_code=500)


# ======================================================
# 🔍 1.1️⃣ Tìm kiếm bài thảo luận theo từ khóa
# ======================================================
@router.get("/search", response_class=HTMLResponse)
async def search_discussions(
    request: Request,
    keyword: str = Query(""),
    db: Session = Depends(get_db)
):
    """Tìm kiếm bài thảo luận theo từ khóa."""
    try:
        discussions = discussion_service.search_discussions(db, keyword)
        return templates["student"].TemplateResponse(
            "discussion/list.html",
            {
                "request": request,
                "discussions": discussions,
                "page_title": f"🔍 Kết quả tìm kiếm: {keyword}",
                "active_page": "discussion",
            },
        )
    except Exception as e:
        print("❌ [Discussion][Search] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tìm kiếm bài thảo luận.</h4>", status_code=500)


# ======================================================
# 🆕 2️⃣ Form tạo bài thảo luận chung (chọn khóa học)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
async def create_general_discussion(request: Request, db: Session = Depends(get_db)):
    """Form tạo bài thảo luận chung."""
    from app.models.course import Course
    courses = db.query(Course).all()

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "courses": courses,
            "page_title": "✏️ Tạo bài thảo luận",
            "active_page": "discussion"
        },
    )


@router.post("/create")
async def create_general_discussion_post(
    request: Request,
    course_id: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    """Xử lý gửi bài thảo luận chung."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if not content.strip():
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "⚠️ Nội dung không được để trống."}, status_code=400
        )

    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "❌ Khóa học không tồn tại."}, status_code=404
        )

    # ✅ Kiểm tra học viên có trong khóa học không
    if not is_student_enrolled(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "⚠️ Bạn chưa đăng ký khóa học này."}, status_code=403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())
        print(f"✅ [Discussion] User={user_id} tạo bài trong Course={course_id}")
        return RedirectResponse(
            url=f"/student/discussion/{course_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        print("❌ [Discussion][CreateGeneral] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tạo bài thảo luận.</h4>", status_code=500)


# ======================================================
# 📘 3️⃣ Danh sách thảo luận theo khóa học (phân trang)
# ======================================================
@router.get("/{course_id}", response_class=HTMLResponse)
async def list_discussions(
    request: Request,
    course_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=5),
    db: Session = Depends(get_db)
):
    """Danh sách bài thảo luận theo khóa học."""
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "❌ Khóa học không tồn tại."}, status_code=404
        )

    discussions_all = discussion_service.get_all_discussions(db, course_id)
    total = len(discussions_all)
    start, end = (page - 1) * limit, page * limit
    discussions = discussions_all[start:end]
    total_pages = ceil(total / limit)

    return templates["student"].TemplateResponse(
        "discussion/list.html",
        {
            "request": request,
            "course": course,
            "discussions": discussions,
            "page": page,
            "total_pages": total_pages,
            "page_title": f"📘 Thảo luận - {course.course_name}",
            "active_page": "discussion",
        },
    )


# ======================================================
# ✏️ 4️⃣ Form tạo bài thảo luận (theo khóa học)
# ======================================================
@router.get("/create/{course_id}", response_class=HTMLResponse)
async def create_discussion_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "❌ Khóa học không tồn tại."}, status_code=404
        )

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "course": course,
            "page_title": "✏️ Tạo bài thảo luận",
            "active_page": "discussion"
        },
    )


# ======================================================
# 📨 5️⃣ Gửi bài thảo luận (POST)
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
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if not content.strip():
        return RedirectResponse(
            url=f"/student/discussion/create/{course_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # ✅ Kiểm tra học viên có trong khóa học
    if not is_student_enrolled(db, user_id, course_id):
        return templates["student"].TemplateResponse(
            "error.html", {"request": request, "message": "⚠️ Bạn chưa đăng ký khóa học này."}, status_code=403
        )

    try:
        discussion_service.add_discussion(db, course_id, user_id, content.strip())
        print(f"✅ [Discussion] User={user_id} ➜ Course={course_id}")
        return RedirectResponse(
            url=f"/student/discussion/{course_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        print("❌ [Discussion][Create] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi gửi bài thảo luận.</h4>", status_code=500)


# ======================================================
# 🔍 6️⃣ Xem chi tiết bài thảo luận
# ======================================================
@router.get("/detail/{discussion_id}", response_class=HTMLResponse)
async def discussion_detail(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    try:
        discussion, replies = discussion_service.get_discussion_with_replies(db, discussion_id)
        if not discussion:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài thảo luận."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "discussion/detail.html",
            {
                "request": request,
                "discussion": discussion,
                "replies": replies,
                "page_title": "📄 Chi tiết thảo luận",
                "active_page": "discussion"
            },
        )
    except Exception as e:
        print("❌ [Discussion][Detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải chi tiết bài thảo luận.</h4>", status_code=500)


# ======================================================
# 💬 7️⃣ Gửi phản hồi (reply, hỗ trợ reply nhiều cấp)
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
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    if not content.strip():
        return RedirectResponse(
            url=f"/student/discussion/detail/{discussion_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    try:
        discussion_service.add_reply(db, discussion_id, user_id, content.strip(), parent_id)
        print(f"💬 [Reply] User={user_id} ➜ Discussion={discussion_id}, parent={parent_id}")
        return RedirectResponse(
            url=f"/student/discussion/detail/{discussion_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        print("❌ [Reply][Add] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi gửi phản hồi.</h4>", status_code=500)


# ======================================================
# 👍 8️⃣ Like / Dislike bài thảo luận
# ======================================================
@router.post("/like/{discussion_id}")
async def like_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        discussion_service.toggle_like(db, discussion_id, user_id)
        print(f"👍 [Like] User={user_id} Discussion={discussion_id}")
        return RedirectResponse(
            url=f"/student/discussion/detail/{discussion_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        print("❌ [Like][Toggle] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xử lý Like/Dislike.</h4>", status_code=500)


# ======================================================
# 🗑️ 9️⃣ Xóa bài thảo luận hoặc phản hồi
# ======================================================
@router.get("/delete/{discussion_id}", response_class=HTMLResponse)
async def delete_discussion(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    """Xóa bài thảo luận (chỉ nếu là người tạo)."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        result = discussion_service.delete_discussion(db, discussion_id, user_id)
        if isinstance(result, dict) and result.get("error"):
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "⚠️ Bạn không có quyền xóa bài thảo luận này."},
                status_code=403,
            )

        print(f"🗑️ [Discussion] User={user_id} đã xóa Discussion={discussion_id}")
        return RedirectResponse(url="/student/discussion/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        print("❌ [Discussion][Delete] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xóa bài thảo luận.</h4>", status_code=500)
