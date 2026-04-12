import traceback

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.config.template_config import templates
from app.database.connection import get_db
from app.services.student import review_service
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment

router = APIRouter(
    prefix="/student/review",
    tags=["Student - Review"]
)


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/", response_class=HTMLResponse)
async def review_home(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        enrolled_courses = (
            db.query(Course)
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.enrollment_status.in_(["approved", "active", "completed"]),
            )
            .distinct()
            .all()
        )

        return templates["student"].TemplateResponse(
            "review/review_list.html",
            {
                "request": request,
                "enrolled_courses": enrolled_courses,
                "active_page": "review",
                "page_title": "Đánh giá khóa học",
            },
        )

    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải danh sách khóa học: {e}", 500)


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def view_course_reviews(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "Không tìm thấy khóa học."},
                status_code=404,
            )

        enrolled = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.enrollment_status.in_(["approved", "active", "completed"]),
            )
            .first()
        )
        if not enrolled:
            return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

        reviews = review_service.get_reviews_by_course(db, course_id)
        average_rating = review_service.get_course_average_rating(db, course_id)

        return templates["student"].TemplateResponse(
            "review/review_course.html",
            {
                "request": request,
                "course": course,
                "reviews": reviews,
                "average_rating": average_rating,
                "page_title": f"Đánh giá khóa học: {course.course_name}",
                "active_page": "review",
            },
        )

    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải đánh giá khóa học: {e}", 500)


@router.get("/submit/{course_id}", response_class=HTMLResponse)
async def review_submit_form(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "Không tìm thấy khóa học."},
                status_code=404,
            )

        enrolled = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.enrollment_status.in_(["approved", "active", "completed"]),
            )
            .first()
        )
        if not enrolled:
            return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

        if review_service.has_student_reviewed(db, course_id, user_id):
            return RedirectResponse(f"/student/review/thanks/{course_id}", status.HTTP_303_SEE_OTHER)

        return templates["student"].TemplateResponse(
            "review/review_submit.html",
            {
                "request": request,
                "course": course,
                "page_title": "Gửi đánh giá khóa học",
                "active_page": "review",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải form đánh giá: {e}", 500)


@router.post("/submit/{course_id}", response_class=HTMLResponse)
async def review_submit_post(
    request: Request,
    course_id: str,
    rating_content: int = Form(...),
    rating_teacher: int = Form(...),
    rating_support: int = Form(...),
    comment: str = Form(...),
    title: str | None = Form(None),
    is_anonymous: bool = Form(False),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "Không tìm thấy khóa học."},
                status_code=404,
            )

        enrolled = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.enrollment_status.in_(["approved", "active", "completed"]),
            )
            .first()
        )
        if not enrolled:
            return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

        if review_service.has_student_reviewed(db, course_id, user_id):
            return RedirectResponse(f"/student/review/thanks/{course_id}", status.HTTP_303_SEE_OTHER)

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

        return RedirectResponse(f"/student/review/thanks/{course_id}", status.HTTP_303_SEE_OTHER)

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        return HTMLResponse(f"Lỗi gửi đánh giá: {e}", 500)


@router.get("/thanks/{course_id}", response_class=HTMLResponse)
async def review_thanks(request: Request, course_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    try:
        course = db.query(Course).filter(Course.id == course_id).first()

        return templates["student"].TemplateResponse(
            "review/review_thanks.html",
            {
                "request": request,
                "course": course,
                "message": "Cảm ơn bạn đã gửi đánh giá. Đánh giá của bạn đang chờ phê duyệt.",
                "page_title": "Cảm ơn bạn đã đánh giá",
                "active_page": "review",
            },
        )

    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi hiển thị trang cảm ơn: {e}", 500)