"""
==========================================================
🎓 ROUTER: Student - Course
Xử lý toàn bộ chức năng khóa học dành cho học viên
Hoàn thiện 100% (Danh sách, Đăng ký, Chi tiết, Tiến độ, Đánh giá, Gợi ý)
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

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
    """Hiển thị danh sách khóa học có thể đăng ký"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        courses = course_service.get_all_courses(db, role="student", search=q)
        return templates["student"].TemplateResponse(
            "course/list.html",
            {
                "request": request,
                "courses": courses,
                "page_title": "🎓 Danh sách khóa học",
                "active_page": "courses",
                "search_query": q or "",
            },
        )
    except Exception as e:
        print("❌ [list_courses] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h3>Lỗi khi tải danh sách khóa học.</h3>", status_code=500)


# =====================================================
# 🎓 2️⃣ Danh sách khóa học đã đăng ký
# =====================================================
@router.get("/enrolled", response_class=HTMLResponse)
async def enrolled_courses(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách khóa học mà học viên đã ghi danh"""
    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    enrollments = course_service.get_enrolled_courses(db, student_id)
    return templates["student"].TemplateResponse(
        "course/enrolled_courses.html",
        {
            "request": request,
            "enrollments": enrollments,
            "page_title": "📘 Khóa học của tôi",
            "active_page": "courses",
        },
    )


# =====================================================
# 📘 3️⃣ Chi tiết khóa học + Gợi ý liên quan
# =====================================================
@router.get("/detail/{course_id}", response_class=HTMLResponse, name="student_course_detail")
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị chi tiết khóa học và gợi ý khóa học liên quan"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        course = course_service.get_course_detail(db, course_id, role="student", user_id=student_id)
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy khóa học."},
                status_code=404,
            )

        # ✅ Lấy danh sách khóa học liên quan
        related_courses = course_service.get_related_courses(db, course_id)

        teacher = course.teacher
        modules = course.modules
        enrolled = course_service.is_student_enrolled(db, student_id, course_id)

        return templates["student"].TemplateResponse(
            "course/detail.html",
            {
                "request": request,
                "course": course,
                "teacher": teacher,
                "modules": modules,
                "enrolled": enrolled,
                "related_courses": related_courses,
                "page_title": f"📖 {course.course_name}",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("❌ [course_detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải chi tiết khóa học.</h4>", status_code=500)


# =====================================================
# 📈 4️⃣ Tiến độ học tập
# =====================================================
@router.get("/progress/{course_id}", response_class=HTMLResponse, name="student_course_progress")
async def course_progress(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị tiến độ học tập của học viên trong khóa học"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        progress_data = course_service.get_course_progress(db, course_id, student_id)
        return templates["student"].TemplateResponse(
            "course/course_progress.html",
            {
                "request": request,
                "course": progress_data.get("course"),
                "modules": progress_data.get("modules"),
                "progress": progress_data.get("progress"),
                "page_title": "📈 Tiến độ học tập",
                "active_page": "courses",
            },
        )
    except Exception as e:
        print("❌ [course_progress] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải tiến độ học tập.</h4>", status_code=500)


# =====================================================
# 🌟 5️⃣ Trang đánh giá khóa học
# =====================================================
@router.get("/feedback/{course_id}", response_class=HTMLResponse, name="student_course_feedback")
async def course_feedback(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Trang xem và gửi đánh giá khóa học"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        feedback = course_service.get_course_feedback(db, course_id)
        enrolled = course_service.is_student_enrolled(db, student_id, course_id)

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
                "page_title": "⭐ Đánh giá khóa học",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("❌ [course_feedback] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải trang đánh giá.</h4>", status_code=500)


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
    db: Session = Depends(get_db),
):
    """Học viên gửi hoặc cập nhật đánh giá khóa học"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        enrolled = course_service.is_student_enrolled(db, student_id, course_id)
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
            print(f"✅ [Feedback] Sinh viên {student_id} đã đánh giá khóa {course_id}")

        return RedirectResponse(
            url=request.url_for("student_course_feedback", course_id=course_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        db.rollback()
        print("❌ [course_feedback_submit] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi gửi đánh giá khóa học.</h4>", status_code=500)


# =====================================================
# 📝 7️⃣ Đăng ký khóa học
# =====================================================
@router.post("/enroll/{course_id}", name="student_course_enroll")
async def enroll_course(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Học viên đăng ký khóa học và chuyển đến danh sách đã ghi danh"""
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        result = course_service.enroll_course(db, student_id, course_id)
        if isinstance(result, dict) and result.get("error"):
            print(f"⚠️ [Enroll] Lỗi đăng ký: {result['error']}")
        else:
            print(f"✅ [Enroll] Sinh viên {student_id} đã đăng ký khóa học {course_id}")

        return RedirectResponse(
            url="/student/course/enrolled",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        db.rollback()
        print("❌ [enroll_course] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi đăng ký khóa học.</h4>", status_code=500)
