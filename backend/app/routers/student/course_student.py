"""
==============================================================
🎓 ROUTER: Student - Course (PRODUCTION 2025 - FINAL 100%)
Tương thích FULL course_service (discount, user_courses, cart_items)
==============================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from sqlalchemy.orm import Session
import traceback

from app.database.connection import get_db
from app.services import course_service
from app.config.template_config import templates

router = APIRouter(
    prefix="/student/course",
    tags=["Student - Course"]
)

# =====================================================
# 📚 1) Danh sách khóa học
# =====================================================
@router.get("/", response_class=HTMLResponse, name="student_course_list")
async def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str = None
):
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        # Lấy tất cả khóa học (public/published)
        courses = course_service.get_all_courses(
            db=db,
            user_id=student_id,
            role="student",
            search=q
        )

        enrolled_ids = course_service.get_enrolled_course_ids(db, student_id)

        purchased_ids = {
            uc.course_id
            for uc in db.query(course_service.UserCourse)
            .filter_by(user_id=student_id)
            .all()
        }

        return templates["student"].TemplateResponse(
            "course/list.html",
            {
                "request": request,
                "courses": courses,
                "enrolled_course_ids": enrolled_ids,
                "purchased_ids": purchased_ids,
                "search_query": q or "",
                "page_title": "🎓 Danh sách khóa học",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("[Student List] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải danh sách.", status_code=500)


# =====================================================
# 🎓 2) Khóa học đã đăng ký
# =====================================================
@router.get("/enrolled", response_class=HTMLResponse, name="student_course_enrolled")
async def enrolled_courses(request: Request, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", 302)

    # Lấy enrollments có join luôn course
    enrollments = (
        db.query(course_service.Enrollment)
        .join(course_service.Course, course_service.Enrollment.course_id == course_service.Course.id)
        .filter(course_service.Enrollment.user_id == student_id)
        .all()
    )

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
# 📘 3) Chi tiết khóa học
# =====================================================
@router.get("/detail/{course_id}", response_class=HTMLResponse, name="student_course_detail")
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):

    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        # Lấy chi tiết course
        course = course_service.get_course_detail(
            db=db,
            course_id=course_id,
            role="student",
            user_id=student_id
        )

        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy khóa học hoặc bạn không có quyền xem."},
                status_code=404,
            )

        teacher = course.teacher
        modules = course.modules
        related = course_service.get_related_courses(db, course_id)

        enrolled = course_service.is_student_enrolled(db, student_id, course_id)
        purchased = course_service.is_course_purchased(db, student_id, course_id)
        in_cart = course_service.is_in_cart(db, student_id, course_id)

        return templates["student"].TemplateResponse(
            "course/detail.html",
            {
                "request": request,
                "course": course,
                "teacher": teacher,
                "modules": modules,
                "related_courses": related,
                "enrolled": enrolled,
                "purchased": purchased,
                "in_cart": in_cart,
                "page_title": f"📘 {course.course_name}",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("[Course Detail] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải chi tiết.", status_code=500)


# =====================================================
# 📈 4) Tiến độ học
# =====================================================
@router.get("/progress/{course_id}", response_class=HTMLResponse, name="student_course_progress")
async def course_progress(request: Request, course_id: str, db: Session = Depends(get_db)):

    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        # Chỉ xem nếu enrolled hoặc purchased
        if not course_service.is_student_enrolled(db, student_id, course_id) and \
           not course_service.is_course_purchased(db, student_id, course_id):
            return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

        result = course_service.get_course_progress(db, course_id, student_id)

        return templates["student"].TemplateResponse(
            "course/course_progress.html",
            {
                "request": request,
                "course": result["course"],
                "modules": result["modules"],
                "progress": result["progress"],
                "page_title": "📈 Tiến độ học tập",
                "active_page": "courses",
            },
        )

    except Exception as e:
        print("[Progress] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi tải tiến độ.", status_code=500)


# =====================================================
# ⭐ 5) Trang danh sách đánh giá
# =====================================================
@router.get("/feedback/{course_id}", response_class=HTMLResponse, name="student_course_feedback")
async def course_feedback(request: Request, course_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", 302)

    result = course_service.get_course_feedback(db, course_id)
    course = result["course"]

    if not course:
        return HTMLResponse("Không tìm thấy khóa học.", status_code=404)

    teacher = course.teacher
    enrolled = course_service.is_student_enrolled(db, student_id, course_id)
    purchased = course_service.is_course_purchased(db, student_id, course_id)

    return templates["student"].TemplateResponse(
        "course/course_feedback.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "reviews": result["reviews"],
            "average_rating": result["average_rating"],
            "enrolled": enrolled or purchased,
            "page_title": "⭐ Đánh giá khóa học",
            "active_page": "courses",
        },
    )


# =====================================================
# ⭐ 6) Submit đánh giá
# =====================================================
@router.post("/feedback/{course_id}", name="student_course_feedback_submit")
async def submit_feedback(
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
    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        # Chỉ đánh giá nếu enrolled hoặc purchased
        if not course_service.is_student_enrolled(db, student_id, course_id) and \
           not course_service.is_course_purchased(db, student_id, course_id):
            return HTMLResponse("Bạn cần tham gia khóa học trước khi đánh giá.", status_code=403)

        course_service.add_course_feedback(
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

        return RedirectResponse(f"/student/course/feedback/{course_id}", status_code=303)

    except Exception as e:
        db.rollback()
        print("[Submit Feedback] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi gửi đánh giá.", status_code=500)


# =====================================================
# 📝 7) Đăng ký khóa học (enroll)
# =====================================================
@router.post("/enroll/{course_id}", name="student_course_enroll")
async def enroll_course(request: Request, course_id: str, db: Session = Depends(get_db)):

    try:
        student_id = request.session.get("user_id")
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        course_service.enroll_course(db, student_id, course_id)

        return RedirectResponse("/student/course/enrolled", status_code=303)

    except Exception as e:
        db.rollback()
        print("[Enroll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi đăng ký khóa học.", status_code=500)
