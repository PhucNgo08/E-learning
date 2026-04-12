from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.module import Module
from app.models.lesson import Lesson
from app.services import course_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/courses",
    tags=["Teacher - Courses"]
)


def safe_int(x):
    if x is None:
        return None
    x = str(x).strip()
    if x == "":
        return None
    try:
        return int(x)
    except Exception:
        return None


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/courses/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    courses = course_service.get_all_courses(db, teacher.id, role="teacher")

    tpl = get_template_by_path(str(request.url.path))
    return tpl.TemplateResponse(
        "courses/list.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now(),
        },
    )


@router.get("/create", response_class=HTMLResponse)
def page_create(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    tpl = get_template_by_path(str(request.url.path))
    return tpl.TemplateResponse(
        "courses/create.html",
        {
            "request": request,
            "teacher": teacher,
            "years": db.query(AcademicYear).all(),
            "major": teacher.major_id,
        },
    )


@router.post("/create")
async def create_course(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),

    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: str = Form("3"),
    subject: str = Form("Other"),
    grade_level: str | None = Form(None),
    difficulty_level: str = Form("beginner"),
    price: float = Form(0),
    semester: str | None = Form(None),

    enrollment_mode: str = Form("auto"),
    max_students: int = Form(100),
    is_public: int = Form(0),
    prerequisites: str | None = Form(None),
    allow_assignments: int = Form(1),
    default_submission_type: str = Form("individual"),
    academic_year_id: str | None = Form(None),

    thumbnail: UploadFile | None = File(None),
):
    teacher = current_teacher

    credit_hours_int = safe_int(credit_hours)
    grade_level_int = safe_int(grade_level)
    semester_int = safe_int(semester)

    if academic_year_id in ("", " ", None):
        academic_year_id = None
    if prerequisites in ("", " ", None):
        prerequisites = None

    major_id = teacher.major_id
    if not major_id:
        raise HTTPException(status_code=400, detail="Giáo viên chưa được gán chuyên ngành (major).")

    allow_assignments_bool = bool(int(allow_assignments))

    await course_service.create_course(
        db=db,
        user_id=teacher.id,
        course_name=course_name,
        description=description,
        credit_hours=credit_hours_int,
        subject=subject,
        grade_level=grade_level_int,
        thumbnail=thumbnail,
        role="teacher",
        difficulty_level=difficulty_level,
        price=price,
        semester=semester_int,
        enrollment_mode=enrollment_mode,
        max_students=max_students,
        is_public=False,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments_bool,
        default_submission_type=default_submission_type,
        academic_year_id=academic_year_id,
        major_id=major_id,
    )

    return RedirectResponse("/teacher/courses/list", status_code=303)


@router.get("/edit/{course_id}", response_class=HTMLResponse)
def page_edit(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    course = course_service.get_course_owned(db, teacher.id, course_id, "teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền.")

    tpl = get_template_by_path(str(request.url.path))
    return tpl.TemplateResponse(
        "courses/edit.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "years": db.query(AcademicYear).all(),
            "major": teacher.major_id,
        },
    )


@router.post("/edit/{course_id}")
async def edit_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),

    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: str = Form("3"),
    status_str: str = Form("draft"),
    subject: str = Form("Other"),
    grade_level: str | None = Form(None),
    difficulty_level: str = Form("beginner"),

    price: float = Form(0),
    semester: str | None = Form(None),
    enrollment_mode: str = Form("auto"),
    max_students: int = Form(100),

    is_public: int = Form(0),
    prerequisites: str | None = Form(None),
    allow_assignments: int = Form(1),
    default_submission_type: str = Form("individual"),

    academic_year_id: str | None = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    teacher = current_teacher

    course = course_service.get_course_owned(db, teacher.id, course_id, "teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền.")

    credit_hours_int = safe_int(credit_hours)
    grade_level_int = safe_int(grade_level)
    semester_int = safe_int(semester)

    if academic_year_id in ("", " ", None):
        academic_year_id = None
    if prerequisites in ("", " ", None):
        prerequisites = None

    allow_assignments_bool = bool(int(allow_assignments))

    await course_service.update_course(
        db=db,
        user_id=teacher.id,
        course_id=course_id,
        course_name=course_name,
        description=description,
        credit_hours=credit_hours_int,
        status_str=course.status,
        subject=subject,
        grade_level=grade_level_int,
        thumbnail=thumbnail,
        role="teacher",
        difficulty_level=difficulty_level,
        price=price,
        semester=semester_int,
        enrollment_mode=enrollment_mode,
        max_students=max_students,
        is_public=course.is_public,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments_bool,
        default_submission_type=default_submission_type,
        academic_year_id=academic_year_id,
        major_id=teacher.major_id,
    )

    return RedirectResponse("/teacher/courses/list", status_code=303)


@router.get("/detail/{course_id}", response_class=HTMLResponse)
def course_detail(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher

    course = course_service.get_course_owned(db, teacher.id, course_id, "teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    modules = (
        db.query(Module)
        .filter(
            Module.course_id == course.id,
            Module.deleted_at.is_(None)
        )
        .order_by(Module.module_number)
        .all()
    )

    for m in modules:
        m.lessons = (
            db.query(Lesson)
            .filter(Lesson.module_id == m.id)
            .order_by(Lesson.lesson_number)
            .all()
        )

    tpl = get_template_by_path(str(request.url.path))
    return tpl.TemplateResponse(
        "courses/detail.html",
        {
            "request": request,
            "course": course,
            "modules": modules,
            "teacher": teacher,
            "teacher_name": teacher.full_name,
            "now": datetime.now(),
        },
    )


@router.get("/manage", response_class=HTMLResponse)
def manage_page(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    teacher = current_teacher
    courses = course_service.get_all_courses(db, teacher.id, role="teacher")

    for c in courses:
        modules = (
            db.query(Module)
            .filter(
                Module.course_id == c.id,
                Module.deleted_at.is_(None)
            )
            .order_by(Module.module_number)
            .all()
        )

        for m in modules:
            m.lessons = (
                db.query(Lesson)
                .filter(Lesson.module_id == m.id)
                .order_by(Lesson.lesson_number)
                .all()
            )

        c.modules = modules

    tpl = get_template_by_path(str(request.url.path))
    return tpl.TemplateResponse(
        "courses/manage.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now(),
        },
    )