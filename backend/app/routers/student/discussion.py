"""
==========================================================
🎓 ROUTER: Student - Discussion
Hiển thị và xử lý chức năng thảo luận học viên trong khóa học
==========================================================
"""

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

# ✅ Import cấu hình template động
from app.config.template_config import templates

# ✅ Import database & service
from app.database.connection import get_db
from app.services.student import discussion_service


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/discussion",
    tags=["Student - Discussion"]
)


# ======================================================
# 🏠 1️⃣ Danh sách tất cả bài thảo luận (mọi khóa học)
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def all_discussions(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị tất cả bài thảo luận của mọi khóa học.
    """
    discussions = discussion_service.get_all_discussions_all_courses(db)
    return templates["student"].TemplateResponse(
        "discussion/list.html",  # ✅ bỏ student/
        {
            "request": request,
            "discussions": discussions,
            "course_id": None,
            "page_title": "💬 Tất cả thảo luận",
            "active_page": "discussion"
        },
    )


# ======================================================
# 🆕 2️⃣ Form tạo bài thảo luận chung (chọn khóa học)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
async def create_general_discussion(request: Request, db: Session = Depends(get_db)):
    """
    Cho phép tạo bài thảo luận chung (chọn khóa học trong form).
    """
    from app.models.course import Course
    courses = db.query(Course).all()

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "course_id": None,
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
    """
    Xử lý gửi bài thảo luận (chọn khóa học thủ công từ form).
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return HTMLResponse("❌ Khóa học không tồn tại.", status_code=400)

    discussion_service.add_discussion(db, course_id, user_id, content.strip())
    return RedirectResponse(
        url=f"/student/discussion/{course_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ======================================================
# 📋 3️⃣ Danh sách thảo luận theo khóa học
# ======================================================
@router.get("/{course_id}", response_class=HTMLResponse)
async def list_discussions(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách bài thảo luận của 1 khóa học cụ thể.
    """
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return HTMLResponse("❌ Khóa học không tồn tại.", status_code=400)

    discussions = discussion_service.get_all_discussions(db, course_id)
    return templates["student"].TemplateResponse(
        "discussion/list.html",
        {
            "request": request,
            "course_id": course_id,
            "course_name": course.course_name,
            "discussions": discussions,
            "page_title": f"📘 Thảo luận - {course.course_name}",
            "active_page": "discussion"
        },
    )


# ======================================================
# 📝 4️⃣ Hiển thị form tạo bài thảo luận mới (GET)
# ======================================================
@router.get("/create/{course_id}", response_class=HTMLResponse)
async def create_discussion_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị form tạo bài thảo luận mới (theo khóa học).
    """
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        return HTMLResponse("❌ Khóa học không tồn tại.", status_code=400)

    return templates["student"].TemplateResponse(
        "discussion/create_post.html",
        {
            "request": request,
            "course_id": course_id,
            "course_name": course.course_name,
            "page_title": "✏️ Tạo bài thảo luận",
            "active_page": "discussion"
        },
    )


# ======================================================
# 📨 5️⃣ Gửi bài thảo luận mới (POST)
# ======================================================
@router.post("/create/{course_id}")
async def create_discussion(
    request: Request,
    course_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Xử lý gửi bài thảo luận mới (theo khóa học cụ thể).
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return HTMLResponse("❌ Khóa học không tồn tại.", status_code=400)

    discussion_service.add_discussion(db, course_id, user_id, content.strip())
    return RedirectResponse(
        url=f"/student/discussion/{course_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ======================================================
# 🔍 6️⃣ Xem chi tiết một bài thảo luận
# ======================================================
@router.get("/detail/{discussion_id}", response_class=HTMLResponse)
async def discussion_detail(request: Request, discussion_id: str, db: Session = Depends(get_db)):
    """
    Xem chi tiết nội dung bài thảo luận và các phản hồi.
    """
    discussion = discussion_service.get_discussion_detail(db, discussion_id)
    if not discussion:
        return HTMLResponse("❌ Không tìm thấy bài thảo luận.", status_code=404)

    return templates["student"].TemplateResponse(
        "discussion/detail.html",
        {
            "request": request,
            "discussion": discussion,
            "page_title": "📄 Chi tiết thảo luận",
            "active_page": "discussion"
        },
    )


# ======================================================
# 💬 7️⃣ Gửi phản hồi (reply) vào bài thảo luận
# ======================================================
@router.post("/reply/{discussion_id}")
async def post_reply(
    request: Request,
    discussion_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Xử lý phản hồi (comment) vào bài thảo luận.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    if not content.strip():
        return RedirectResponse(
            url=f"/student/discussion/detail/{discussion_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    discussion_service.add_reply(db, discussion_id, user_id, content.strip())

    return RedirectResponse(
        url=f"/student/discussion/detail/{discussion_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )
