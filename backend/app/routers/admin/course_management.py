from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, Query
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.course import Course
from app.models.user import User
from app.services import course_service

from app.config.template_config import get_template_by_path

course_router = APIRouter(
    prefix="/admin/Course",
    tags=["Admin - Course Management"]
)

# =====================================================================================
# 📋 1) Danh sách khóa học
# =====================================================================================
@course_router.get("/manage", response_class=HTMLResponse)
async def manage_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(None),
    status: str = Query(None),
    teacher_id: str = Query(None),
    major_id: str = Query(None),
    year_id: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = 10
):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    tpl = get_template_by_path(request.url.path)

    query = db.query(Course).join(User, Course.teacher_id == User.id, isouter=True)

    if q:
        query = query.filter(
            Course.course_name.ilike(f"%{q}%") |
            Course.course_code.ilike(f"%{q}%")
        )
    if status:
        query = query.filter(Course.status == status)
    if teacher_id:
        query = query.filter(Course.teacher_id == teacher_id)
    if major_id:
        query = query.filter(Course.major_id == major_id)
    if year_id:
        query = query.filter(Course.academic_year_id == year_id)

    total = query.count()
    total_pages = (total + per_page - 1) // per_page

    courses = (
        query.order_by(Course.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return tpl.TemplateResponse(
        "Course/manage.html",
        {
            "request": request,
            "courses": courses,
            "teachers": db.query(User).filter(User.role == "teacher").all(),
            "majors": db.query(Major).all(),
            "years": db.query(AcademicYear).all(),
            "total": total,
            "current_page": page,
            "total_pages": total_pages,
            "q": q,
            "status": status,
            "teacher_id": teacher_id,
            "major_id": major_id,
            "year_id": year_id,
        }
    )

# =====================================================================================
# ➕ 2) GET: Trang tạo khóa học
# =====================================================================================
@course_router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    tpl = get_template_by_path(request.url.path)

    return tpl.TemplateResponse(
        "Course/create.html",
        {
            "request": request,
            "teachers": db.query(User).filter(User.role == "teacher").all(),
            "years": db.query(AcademicYear).all(),
            "majors": db.query(Major).all(),
        },
    )

# =====================================================================================
# 💾 3) POST: Tạo khóa học FULL 24 FIELD
# =====================================================================================
@course_router.post("/create")
async def create_course(
    request: Request,
    db: Session = Depends(get_db),

    # --- Core fields ---
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    subject: str = Form("Other"),
    grade_level: int | None = Form(None),

    # --- Admin fields ---
    teacher_id: str | None = Form(None),
    academic_year_id: str | None = Form(None),
    major_id: str | None = Form(None),
    semester: int | None = Form(None),

    # --- Pricing ---
    price: float = Form(0),

    # --- Course metadata ---
    course_type: str = Form("online"),
    difficulty_level: str = Form("beginner"),
    enrollment_mode: str = Form("auto"),
    max_students: int = Form(100),
    is_public: int = Form(0),

    prerequisites: str | None = Form(None),
    allow_assignments: int = Form(1),
    default_submission_type: str = Form("individual"),

    # --- Date fields ---
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),

    # --- File ---
    thumbnail: UploadFile | None = File(None),
):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    # 1) Tạo khóa học cơ bản
    new_course = await course_service.create_course(
        db=db,
        user_id=request.session.get("user_id"),
        course_name=course_name,
        description=description,
        credit_hours=credit_hours,
        subject=subject,
        grade_level=grade_level,
        thumbnail=thumbnail,
        role="admin",
        teacher_id=teacher_id,
        major_id=major_id,
        academic_year_id=academic_year_id,
        semester=semester,
        price=price,
        difficulty_level=difficulty_level,
        enrollment_mode=enrollment_mode,
        max_students=max_students,
        is_public=is_public,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments,
        default_submission_type=default_submission_type,
    )

    # 2) Kiểm tra lỗi
    if isinstance(new_course, dict) and "error" in new_course:
        raise HTTPException(400, new_course["error"])

    # 3) Gán thông tin bổ sung
    new_course.course_type = course_type
    if start_date:
        new_course.start_date = start_date
    if end_date:
        new_course.end_date = end_date

    db.commit()

    return RedirectResponse("/admin/Course/manage", status_code=303)

# =====================================================================================
# ✏️ 4) GET: Trang edit khóa học
# =====================================================================================
@course_router.get("/edit/{course_id}", response_class=HTMLResponse)
async def page_edit(course_id: str, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    tpl = get_template_by_path(request.url.path)

    course = course_service.get_course_owned(
        db, request.session.get("user_id"), course_id, role="admin"
    )

    if not course:
        raise HTTPException(404, "Không tìm thấy khóa học.")

    return tpl.TemplateResponse(
        "Course/edit.html",
        {
            "request": request,
            "course": course,
            "teachers": db.query(User).filter(User.role == "teacher").all(),
            "years": db.query(AcademicYear).all(),
            "majors": db.query(Major).all(),
        },
    )

# =====================================================================================
# 💾 5) POST: Cập nhật khóa học FULL
# =====================================================================================
@course_router.post("/edit/{course_id}")
async def update_course_action(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),

    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    status_str: str = Form("draft"),
    subject: str = Form("Other"),
    grade_level: int | None = Form(None),

    teacher_id: str | None = Form(None),
    academic_year_id: str | None = Form(None),
    major_id: str | None = Form(None),
    semester: int | None = Form(None),

    price: float = Form(0),
    course_type: str = Form("online"),
    difficulty_level: str = Form("beginner"),
    enrollment_mode: str = Form("auto"),
    max_students: int = Form(100),
    is_public: int = Form(0),

    prerequisites: str | None = Form(None),
    allow_assignments: int = Form(1),
    default_submission_type: str = Form("individual"),

    start_date: str | None = Form(None),
    end_date: str | None = Form(None),

    thumbnail: UploadFile | None = File(None),
):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    updated = await course_service.update_course(
        db=db,
        user_id=request.session.get("user_id"),
        course_id=course_id,
        course_name=course_name,
        description=description,
        credit_hours=credit_hours,
        status_str=status_str,
        subject=subject,
        grade_level=grade_level,
        thumbnail=thumbnail,
        role="admin",
        teacher_id=teacher_id,
        major_id=major_id,
        academic_year_id=academic_year_id,
        price=price,
        difficulty_level=difficulty_level,
        enrollment_mode=enrollment_mode,
        max_students=max_students,
        semester=semester,
        is_public=is_public,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments,
        default_submission_type=default_submission_type,
    )

    if isinstance(updated, dict) and "error" in updated:
        raise HTTPException(400, updated["error"])

    course = db.query(Course).filter(Course.id == course_id).first()
    course.course_type = course_type
    course.start_date = start_date or None
    course.end_date = end_date or None

    db.commit()

    return RedirectResponse("/admin/Course/manage", status_code=303)

# =====================================================================================
# ❌ 6) Xóa khóa học
# =====================================================================================
@course_router.post("/delete/{course_id}")
async def delete_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    ok = course_service.delete_course(db, request.session.get("user_id"), course_id, role="admin")

    if not ok:
        raise HTTPException(404, "Không thể xóa khóa học.")

    return RedirectResponse("/admin/Course/manage", status_code=303)

# =====================================================================================
# 📘 7) Chi tiết khóa học
# =====================================================================================
@course_router.get("/detail/{course_id}", response_class=HTMLResponse)
async def course_detail(course_id: str, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    tpl = get_template_by_path(request.url.path)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(404, "Không tìm thấy khóa học.")

    teacher = db.query(User).filter(User.id == course.teacher_id).first()

    return tpl.TemplateResponse(
        "Course/detail.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "now": datetime.now(),
        },
    )

# =====================================================================================
# 📊 8) Tổng quan khóa học
# =====================================================================================
@course_router.get("/overview", response_class=HTMLResponse)
async def course_overview(request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)

    tpl = get_template_by_path(request.url.path)

    return tpl.TemplateResponse(
        "Course/overview.html",
        {
            "request": request,
            "total_courses": db.query(Course).count(),
            "total_teachers": db.query(User).filter(User.role == "teacher").count(),
            "total_students": db.query(User).filter(User.role == "student").count(),
            "course": db.query(Course).order_by(Course.created_at.desc()).first(),
        },
    )
