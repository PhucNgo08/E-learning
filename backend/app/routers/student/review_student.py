"""
==========================================================
🎓 ROUTER: Student - Review
Chức năng đánh giá khóa học dành cho sinh viên:
- Xem danh sách các khóa học đã ghi danh
- Xem đánh giá từng khóa học
- Gửi đánh giá mới
- Trang cảm ơn
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form, status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

# ✅ Import cấu hình
from app.config.template_config import templates
from app.database.connection import get_db

# ✅ Import service & model
from app.services.student import review_service
from app.models.course import Course
from app.models.enrollment import Enrollment


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/review",
    tags=["Student - Review"]
)


# ======================================================
# 🏠 1️⃣ Trang danh sách khóa học để đánh giá
# ======================================================
@router.get("/", response_class=HTMLResponse)
async def review_home(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách tất cả khóa học mà sinh viên đã ghi danh
    để xem hoặc gửi đánh giá.
    """
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    # 📘 Lấy danh sách khóa học mà sinh viên đã ghi danh
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
            "now": datetime.utcnow(),
        },
    )


# ======================================================
# 🧾 2️⃣ Xem danh sách đánh giá của một khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def view_course_reviews(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách đánh giá cho một khóa học cụ thể.
    """
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "Không tìm thấy khóa học."},
        )

    reviews = await review_service.get_reviews_by_course(course_id, db)
    average_rating = await review_service.get_course_average_rating(db, course_id)

    return templates["student"].TemplateResponse(
        "review/review_course.html",
        {
            "request": request,
            "course": course,
            "reviews": reviews,
            "average_rating": average_rating,
            "active_page": "review",
        },
    )


# ======================================================
# 📝 3️⃣ Form gửi đánh giá khóa học
# ======================================================
@router.get("/submit/{course_id}", response_class=HTMLResponse)
async def review_submit_form(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị form để sinh viên gửi đánh giá.
    """
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "student":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "Không tìm thấy khóa học để đánh giá."},
        )

    if await review_service.has_student_reviewed(db, course_id, user_id):
        return RedirectResponse(
            url=f"/student/review/thanks/{course_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates["student"].TemplateResponse(
        "review/review_submit.html",
        {
            "request": request,
            "course": course,
            "active_page": "review",
        },
    )


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
    """
    Xử lý khi sinh viên gửi đánh giá khóa học.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "Không tìm thấy khóa học để đánh giá."},
        )

    if await review_service.has_student_reviewed(db, course_id, user_id):
        return RedirectResponse(
            url=f"/student/review/thanks/{course_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    await review_service.submit_review(
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
        url=f"/student/review/thanks/{course_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ======================================================
# 🙏 5️⃣ Trang cảm ơn
# ======================================================
@router.get("/thanks/{course_id}", response_class=HTMLResponse)
async def review_thanks(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Hiển thị trang cảm ơn sau khi sinh viên gửi đánh giá.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    course = db.query(Course).filter(Course.id == course_id).first()

    return templates["student"].TemplateResponse(
        "review/review_thanks.html",
        {
            "request": request,
            "course": course,
            "message": "🎉 Cảm ơn bạn đã gửi đánh giá! Đánh giá của bạn đang chờ phê duyệt.",
            "active_page": "review",
        },
    )
