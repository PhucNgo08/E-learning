import traceback
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import templates
from app.database.connection import get_db
from app.models.major import Major
from app.services import course_service

router = APIRouter(prefix="/student/course", tags=["Student - Course"])


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


@router.get("/", response_class=HTMLResponse, name="student_course_list")
async def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    major_id: str | None = None,
    difficulty_level: str | None = None,
    price_filter: str | None = None,
    sort: str | None = "newest",
):
    try:
        student_id = get_current_student_id(request)
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        if major_id in ("", "all", None):
            major_id = None
        if difficulty_level in ("", "all", None):
            difficulty_level = None
        if price_filter in ("", "all", None):
            price_filter = None

        courses = course_service.get_all_courses(
            db=db,
            user_id=student_id,
            role="student",
            search=q,
            major_id=major_id,
            difficulty_level=difficulty_level,
            price_filter=price_filter,
            sort=sort,
        )

        majors = (
            db.query(Major)
            .filter(Major.is_active.is_(True))
            .order_by(Major.major_name.asc())
            .all()
        )

        enrolled_ids = set(course_service.get_enrolled_course_ids(db, student_id) or [])
        purchased_ids = set(course_service.get_purchased_course_ids(db, student_id) or [])

        return templates["student"].TemplateResponse(
            "course/list.html",
            {
                "request": request,
                "courses": courses,
                "majors": majors,
                "enrolled_course_ids": enrolled_ids,
                "purchased_ids": purchased_ids,
                "search_query": q or "",
                "selected_major_id": major_id or "",
                "selected_difficulty": difficulty_level or "",
                "selected_price_filter": price_filter or "",
                "selected_sort": sort or "newest",
                "page_title": "Danh sách khóa học",
                "active_page": "courses",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải danh sách khóa học: {e}", status_code=500)


@router.get("/enrolled", response_class=HTMLResponse, name="student_course_enrolled")
async def enrolled_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = None,
    major_id: str | None = None,
    difficulty_level: str | None = None,
    progress_filter: str | None = None,
    sort: str | None = "name_asc",
):
    student_id = get_current_student_id(request)
    if not student_id:
        return RedirectResponse("/auth/login", 302)

    if major_id in ("", "all", None):
        major_id = None
    if difficulty_level in ("", "all", None):
        difficulty_level = None
    if progress_filter in ("", "all", None):
        progress_filter = None

    courses = course_service.get_enrolled_courses(
        db=db,
        user_id=student_id,
        search=q,
        major_id=major_id,
        difficulty_level=difficulty_level,
        progress_filter=progress_filter,
        sort=sort,
    )

    majors = (
        db.query(Major)
        .filter(Major.is_active.is_(True))
        .order_by(Major.major_name.asc())
        .all()
    )

    return templates["student"].TemplateResponse(
        "course/enrolled_courses.html",
        {
            "request": request,
            "courses": courses,
            "majors": majors,
            "search_query": q or "",
            "selected_major_id": major_id or "",
            "selected_difficulty": difficulty_level or "",
            "selected_progress_filter": progress_filter or "",
            "selected_sort": sort or "name_asc",
            "page_title": "Khóa học của tôi",
            "active_page": "courses",
        },
    )


@router.get("/detail/{course_id}", response_class=HTMLResponse, name="student_course_detail")
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):
    try:
        student_id = get_current_student_id(request)
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        course = course_service.get_course_detail(
            db=db,
            course_id=course_id,
            role="student",
            user_id=student_id,
        )
        if not course:
            return templates["student"].TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "message": "Không tìm thấy khóa học hoặc bạn không có quyền xem.",
                },
                status_code=404,
            )

        flags = course_service.get_student_course_access_flags(db, student_id, course_id)

        return templates["student"].TemplateResponse(
            "course/detail.html",
            {
                "request": request,
                "course": course,
                "teacher": getattr(course, "teacher", None),
                "modules": getattr(course, "modules", []),
                "related_courses": course_service.get_related_courses(db, course_id),
                "enrolled": flags["enrolled"],
                "purchased": flags["purchased"],
                "in_cart": course_service.is_in_cart(db, student_id, course_id),
                "page_title": course.course_name,
                "active_page": "courses",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải chi tiết khóa học: {e}", status_code=500)


@router.get("/progress/{course_id}", response_class=HTMLResponse, name="student_course_progress")
async def course_progress(request: Request, course_id: str, db: Session = Depends(get_db)):
    try:
        student_id = get_current_student_id(request)
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        if not course_service.can_access_course(db, student_id, course_id):
            return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

        result = course_service.get_course_progress(db, course_id, student_id)
        if not result.get("course"):
            return templates["student"].TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "message": "Không tìm thấy khóa học.",
                },
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "course/course_progress.html",
            {
                "request": request,
                "course": result.get("course"),
                "modules": result.get("modules", []),
                "progress": result.get("progress", {}),
                "next_lesson_id": result.get("next_lesson_id"),
                "page_title": "Tiến độ học tập",
                "active_page": "courses",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"Lỗi tải tiến độ: {e}", status_code=500)


@router.get("/feedback/{course_id}", response_class=HTMLResponse, name="student_course_feedback")
async def course_feedback(request: Request, course_id: str, db: Session = Depends(get_db)):
    student_id = get_current_student_id(request)
    if not student_id:
        return RedirectResponse("/auth/login", 302)

    result = course_service.get_course_feedback(db, course_id)
    course = result.get("course")
    if not course:
        return HTMLResponse("Không tìm thấy khóa học.", status_code=404)

    flags = course_service.get_student_course_access_flags(db, student_id, course_id)
    is_public_preview = bool(getattr(course, "is_public", False)) and str(getattr(course, "status", "")).lower() == "published"

    if not flags["can_access"] and not is_public_preview:
        return HTMLResponse("Bạn không có quyền xem đánh giá của khóa học này.", status_code=403)

    return templates["student"].TemplateResponse(
        "course/course_feedback.html",
        {
            "request": request,
            "course": course,
            "teacher": getattr(course, "teacher", None),
            "reviews": result.get("reviews", []),
            "average_rating": result.get("average_rating", 0),
            "enrolled": flags["can_access"],
            "page_title": "Đánh giá khóa học",
            "active_page": "courses",
        },
    )


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
        student_id = get_current_student_id(request)
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        if not course_service.can_access_course(db, student_id, course_id):
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
        traceback.print_exc()
        return HTMLResponse(f"Lỗi gửi đánh giá: {e}", status_code=500)


@router.post("/enroll/{course_id}", name="student_course_enroll")
async def enroll_course(request: Request, course_id: str, db: Session = Depends(get_db)):
    try:
        student_id = get_current_student_id(request)
        if not student_id:
            return RedirectResponse("/auth/login", 302)

        course_service.enroll_course(db=db, user_id=student_id, course_id=course_id)
        return RedirectResponse(
            f"/student/course/detail/{course_id}?success={quote('Đăng ký thành công')}",
            status_code=303,
        )
    except Exception as e:
        return RedirectResponse(
            f"/student/course/detail/{course_id}?error={quote(str(e))}",
            status_code=303,
        )