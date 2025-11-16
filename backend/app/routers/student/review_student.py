"""
==========================================================
🎓 ROUTER: Student - Review
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime
import traceback

# Config
from app.config.template_config import templates
from app.database.connection import get_db

# Services
from app.services.student import review_service

# Models
from app.models.course import Course
from app.models.enrollment import Enrollment


router = APIRouter(
    prefix="/student/review",
    tags=["Student - Review"]
)

# ======================================================
# 🏠 1️⃣ Danh sách khóa học đã ghi danh
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def review_home(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        enrolled_courses = (
            db.query(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == user_id)
            .all()
        )

        return templates["student"].TemplateResponse(
            "review/review_list.html",
            {
                "request": request,
                "enrolled_courses": enrolled_courses,
                "active_page": "review",
                "page_title": "⭐ Đánh giá khóa học",
            },
        )

    except Exception as e:
        print("❌ [Review][Home] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải danh sách khóa học.", 500)


# ======================================================
# 🧾 2️⃣ Xem đánh giá của 1 khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def view_course_reviews(request: Request, course_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy khóa học."},
                404,
            )

        # ❗ FIX: bỏ await + truyền đúng thứ tự
        reviews = review_service.get_reviews_by_course(db, course_id)
        average_rating = review_service.get_course_average_rating(db, course_id)

        return templates["student"].TemplateResponse(
            "review/review_course.html",
            {
                "request": request,
                "course": course,
                "reviews": reviews,
                "average_rating": average_rating,
                "page_title": f"📖 Đánh giá khóa học: {course.course_name}",
                "active_page": "review",
            },
        )

    except Exception as e:
        print("❌ [Review][ViewCourse] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải đánh giá khóa học.", 500)


# ======================================================
# 📝 3️⃣ Form gửi đánh giá
# ======================================================
@router.get("/submit/{course_id}", response_class=HTMLResponse)
async def review_submit_form(request: Request, course_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy khóa học."},
                404,
            )

        # ❗ FIX: bỏ await
        if review_service.has_student_reviewed(db, course_id, user_id):
            return RedirectResponse(
                f"/student/review/thanks/{course_id}",
                status.HTTP_303_SEE_OTHER,
            )

        return templates["student"].TemplateResponse(
            "review/review_submit.html",
            {
                "request": request,
                "course": course,
                "page_title": "📝 Gửi đánh giá khóa học",
                "active_page": "review",
            },
        )
    except Exception as e:
        print("❌ [Review][SubmitForm] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải form đánh giá.", 500)


# ======================================================
# 📤 4️⃣ Xử lý POST gửi đánh giá
# ======================================================
@router.post("/submit/{course_id}", response_class=HTMLResponse)
async def review_submit_post(
    request: Request,
    course_id: str,
    rating_content: int = Form(...),
    rating_teacher: int = Form(...),
    rating_support: int = Form(...),
    comment: str = Form(...),
    title: str = Form(None),
    is_anonymous: bool = Form(False),
    db: Session = Depends(get_db),
):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy khóa học."},
                404,
            )

        # ❗ FIX: bỏ await
        if review_service.has_student_reviewed(db, course_id, user_id):
            return RedirectResponse(
                f"/student/review/thanks/{course_id}",
                status.HTTP_303_SEE_OTHER,
            )

        # ❗ FIX: bỏ await
        review_service.submit_review(
            db=db,
            course_id=course_id,
            user_id=user_id,
            rating_content=rating_content,
            rating_teacher=rating_teacher,
            rating_support=rating_support,
            comment=comment,
            title=title,
            is_anonymous=is_anonymous,
        )

        return RedirectResponse(
            f"/student/review/thanks/{course_id}",
            status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        db.rollback()
        print("❌ [Review][SubmitPost] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi gửi đánh giá.", 500)


# ======================================================
# 🙏 5️⃣ Trang cảm ơn
# ======================================================
@router.get("/thanks/{course_id}", response_class=HTMLResponse)
async def review_thanks(request: Request, course_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()

        return templates["student"].TemplateResponse(
            "review/review_thanks.html",
            {
                "request": request,
                "course": course,
                "message": "🎉 Cảm ơn bạn đã gửi đánh giá! Đánh giá của bạn đang chờ phê duyệt.",
                "page_title": "🙏 Cảm ơn bạn đã đánh giá",
                "active_page": "review",
            },
        )

    except Exception as e:
        print("❌ [Review][Thanks] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi hiển thị trang cảm ơn.", 500)
