from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.connection import get_db
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.user import User
from app.services import course_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path


# =====================================================
# 🚀 Router
# =====================================================
router = APIRouter(
    prefix="/teacher/courses",
    tags=["Teacher - Courses"]
)


# =====================================================
# 🧭 0️⃣ Redirect gốc → /list
# =====================================================
@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/teacher/courses/list", status_code=303)


# =====================================================
# 📋 1️⃣ Danh sách khóa học của giáo viên
# =====================================================
@router.get("/list", response_class=HTMLResponse)
def list_courses(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách khóa học của giáo viên."""
    teacher = current_teacher
    courses = course_service.get_all_courses(db, teacher.id, role="teacher")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "courses/list.html",
        {"request": request, "teacher": teacher, "courses": courses, "now": datetime.now()},
    )


# =====================================================
# ➕ 2️⃣ Tạo khóa học
# =====================================================
@router.get("/create", response_class=HTMLResponse)
def page_create(
    request: Request,
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form tạo khóa học."""
    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "courses/create.html", {"request": request, "teacher_name": current_teacher.full_name}
    )


@router.post("/create")
async def create_course(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    subject: str = Form("Other"),
    grade_level: int | None = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    """Xử lý tạo khóa học."""
    teacher_id = current_teacher.id
    result = await course_service.create_course(
        db, teacher_id, course_name, description,
        credit_hours, subject, grade_level, thumbnail,
        role="teacher"
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/courses/list", status_code=303)


# =====================================================
# ✏️ 3️⃣ Sửa khóa học
# =====================================================
@router.get("/edit/{course_id}", response_class=HTMLResponse)
def page_edit(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    course = course_service.get_course_owned(db, teacher_id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "courses/edit.html", {"request": request, "course": course}
    )


@router.post("/edit/{course_id}")
async def edit_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    status_str: str = Form("draft"),
    subject: str = Form("Other"),
    grade_level: int | None = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    teacher_id = current_teacher.id
    result = await course_service.update_course(
        db, teacher_id, course_id,
        course_name, description, credit_hours,
        status_str, subject, grade_level, thumbnail,
        role="teacher"
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse("/teacher/courses/list", status_code=303)


# =====================================================
# ❌ 4️⃣ Xóa khóa học
# =====================================================
@router.post("/delete/{course_id}")
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    ok = course_service.delete_course(db, teacher_id, course_id, role="teacher")
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy hoặc không có quyền xóa khóa học.")

    return RedirectResponse("/teacher/courses/list", status_code=303)


# =====================================================
# 📘 5️⃣ Chi tiết khóa học
# =====================================================
@router.get("/detail/{course_id}", response_class=HTMLResponse)
def course_detail(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    course = course_service.get_course_owned(db, teacher_id, course_id, role="teacher")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    modules = (
        db.query(Module)
        .filter(Module.course_id == course.id)
        .order_by(Module.module_number.asc())
        .all()
    )
    for m in modules:
        m.lessons = (
            db.query(Lesson)
            .filter(Lesson.module_id == m.id)
            .order_by(Lesson.lesson_number.asc())
            .all()
        )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "courses/detail.html",
        {"request": request, "course": course, "modules": modules, "teacher_name": current_teacher.full_name},
    )


# =====================================================
# 🧩 6️⃣ Trang quản lý tổng hợp (course + module + lesson)
# =====================================================
@router.get("/manage", response_class=HTMLResponse)
def manage_courses(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    teacher = current_teacher
    courses = course_service.get_all_courses(db, teacher_id, role="teacher")

    for c in courses:
        modules = (
            db.query(Module)
            .filter(Module.course_id == c.id)
            .order_by(Module.module_number.asc())
            .all()
        )
        for m in modules:
            m.lessons = (
                db.query(Lesson)
                .filter(Lesson.module_id == m.id)
                .order_by(Lesson.lesson_number.asc())
                .all()
            )
        c.modules = modules

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "courses/manage.html",
        {"request": request, "teacher": teacher, "courses": courses, "now": datetime.now()},
    )
