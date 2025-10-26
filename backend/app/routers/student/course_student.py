"""
==========================================================
🎓 ROUTER: Student - Course
Xử lý các chức năng khóa học của học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime
import uuid

# === Import Database & Service ===
from app.database.connection import get_db
from app.services import course_service

# === Import Models cần dùng ===
from app.models.course import Course
from app.models.enrollment import Enrollment

# === Import template động ===
from app.config.template_config import templates


# =====================================================
# ⚙️ Cấu hình Router
# =====================================================
router = APIRouter(prefix="/student/course", tags=["Student - Course"])


# =====================================================
# 📚 1️⃣ Danh sách khóa học đang mở
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def list_courses(request: Request, db: Session = Depends(get_db), q: str = None):
    """Danh sách khóa học có thể đăng ký"""
    courses = course_service.get_all_courses(db, role="student", search=q)
    return templates["student"].TemplateResponse(
        "course/list.html",  # ✅ ĐÃ BỎ student/ vì đã trỏ sẵn đến thư mục student/
        {
            "request": request,
            "courses": courses,
            "active_page": "courses",
        },
    )


# =====================================================
# 🎓 2️⃣ Danh sách khóa học đã đăng ký
# =====================================================
@router.get("/enrolled", response_class=HTMLResponse)
async def enrolled_courses(request: Request, db: Session = Depends(get_db)):
    """Danh sách khóa học mà học viên đã ghi danh"""
    student_id = request.session.get("user_id", "demo-student")
    enrollments = course_service.get_enrolled_courses(db, student_id)
    return templates["student"].TemplateResponse(
        "course/enrolled_courses.html",
        {
            "request": request,
            "enrollments": enrollments,
            "active_page": "courses",
        },
    )


# =====================================================
# 📘 3️⃣ Chi tiết khóa học
# =====================================================
@router.get("/detail/{course_id}", response_class=HTMLResponse, name="student_course_detail")
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị chi tiết khóa học"""
    course = course_service.get_course_detail(db, course_id, role="student")
    if not course:
        return HTMLResponse("<h3>Không tìm thấy khóa học hoặc bạn chưa được phép truy cập.</h3>", status_code=404)

    teacher = course.teacher
    modules = course.modules

    student_id = request.session.get("user_id", "demo-student")
    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.user_id == student_id)
        .first()
        is not None
    )

    return templates["student"].TemplateResponse(
        "course/detail.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "modules": modules,
            "enrolled": enrolled,
            "active_page": "courses",
        },
    )


# =====================================================
# 📈 4️⃣ Tiến độ học tập
# =====================================================
@router.get("/progress/{course_id}", response_class=HTMLResponse, name="student_course_progress")
async def course_progress(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị tiến độ học tập của học viên trong khóa học"""
    student_id = request.session.get("user_id", "demo-student")
    progress_data = course_service.get_course_progress(db, course_id, student_id)

    return templates["student"].TemplateResponse(
        "course/course_progress.html",
        {
            "request": request,
            "course": progress_data.get("course"),
            "modules": progress_data.get("modules"),
            "progress": progress_data.get("progress"),
            "active_page": "courses",
        },
    )


# =====================================================
# 🌟 5️⃣ Đánh giá khóa học
# =====================================================
@router.get("/feedback/{course_id}", response_class=HTMLResponse, name="student_course_feedback")
async def course_feedback(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Trang xem và gửi đánh giá khóa học"""
    feedback = course_service.get_course_feedback(db, course_id)
    student_id = request.session.get("user_id", "demo-student")

    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course_id, Enrollment.user_id == student_id)
        .first()
        is not None
    )

    course = feedback.get("course")
    teacher = course.teacher if course else None

    return templates["student"].TemplateResponse(
        "course/course_feedback.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "reviews": feedback.get("reviews"),
            "average_rating": feedback.get("average_rating"),
            "enrolled": enrolled,
            "active_page": "courses",
        },
    )


# =====================================================
# 🧾 6️⃣ Gửi đánh giá khóa học (POST)
# =====================================================
@router.post("/feedback/{course_id}", name="student_course_feedback_submit")
async def course_feedback_submit(
    request: Request,
    course_id: str,
    title: str = Form(...),
    comment: str = Form(...),
    overall_rating: int = Form(...),
    rating_content: int = Form(...),
    rating_teacher: int = Form(...),
    rating_support: int = Form(...),
    db: Session = Depends(get_db)
):
    """Học viên gửi hoặc cập nhật đánh giá khóa học"""
    try:
        student_id = request.session.get("user_id", "demo-student")

        enrolled = (
            db.query(Enrollment)
            .filter(Enrollment.course_id == course_id, Enrollment.user_id == student_id)
            .first()
        )
        if not enrolled:
            return HTMLResponse("<h4>Bạn cần đăng ký khóa học trước khi đánh giá.</h4>", status_code=403)

        result = course_service.add_course_feedback(
            db=db,
            course_id=course_id,
            user_id=student_id,
            title=title,
            comment=comment,
            overall_rating=overall_rating,
            rating_content=rating_content,
            rating_teacher=rating_teacher,
            rating_support=rating_support,
        )

        if result:
            print(f"✅ Học viên {student_id} đã gửi/cập nhật đánh giá cho khóa {course_id}")

        return RedirectResponse(
            url=request.url_for("student_course_feedback", course_id=course_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        print("❌ [course_feedback_submit] Exception:", e)
        return HTMLResponse("<h4>Lỗi khi gửi đánh giá.</h4>", status_code=500)


# =====================================================
# 📝 7️⃣ Đăng ký khóa học
# =====================================================
@router.post("/enroll/{course_id}", name="student_course_enroll")
async def enroll_course(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Học viên đăng ký khóa học.
    Sau khi đăng ký thành công → chuyển đến danh sách đã ghi danh.
    """
    try:
        student_id = request.session.get("user_id", "demo-student")

        result = course_service.enroll_course(db, student_id, course_id)
        if isinstance(result, dict) and result.get("error"):
            print("❌ Lỗi đăng ký:", result["error"])
        else:
            print(f"✅ Student {student_id} đăng ký khóa học {course_id}")

    except Exception as e:
        print("❌ Exception enroll:", e)

    return RedirectResponse(
        url="/student/course/enrolled",
        status_code=status.HTTP_303_SEE_OTHER,
    )
