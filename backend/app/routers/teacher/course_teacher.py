from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.course import Course
from app.models.user import User
from app.models.module import Module
from app.models.lesson import Lesson
from app.services.teacher import course_service
from datetime import datetime
from pathlib import Path

# ==============================
# 🧭 Template Configuration
# ==============================
# ✅ Trỏ đến thư mục templates gốc (chuẩn cho toàn dự án)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ==============================
# 🚀 Router
# ==============================
router = APIRouter(prefix="/teacher/courses", tags=["Teacher - Courses"])

# =====================================================
# 📋 Danh sách khóa học của giáo viên
# =====================================================
@router.get("/list", response_class=HTMLResponse)
def list_courses(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    # ✅ Kiểm tra quyền
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()
    courses = db.query(Course).filter(Course.teacher_id == user_id).all()

    return templates.TemplateResponse(
        "teacher/courses/list.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "now": datetime.now(),
        },
    )

# =====================================================
# ➕ Tạo khóa học
# =====================================================
@router.get("/create", response_class=HTMLResponse)
def page_create(request: Request):
    role = request.session.get("role")
    if role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    return templates.TemplateResponse("teacher/courses/create.html", {"request": request})


@router.post("/create")
async def create_course(
    request: Request,
    db: Session = Depends(get_db),
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    subject: str = Form("Other"),
    grade_level: int = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    await course_service.create_course(
        db, user_id, course_name, description, credit_hours, subject, grade_level, thumbnail
    )
    return RedirectResponse(url="/teacher/courses/list", status_code=303)

# =====================================================
# ✏️ Chỉnh sửa khóa học
# =====================================================
@router.get("/edit/{course_id}", response_class=HTMLResponse)
def page_edit(course_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    course = course_service.get_course_owned(db, user_id, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền.")

    return templates.TemplateResponse(
        "teacher/courses/edit.html", {"request": request, "course": course}
    )


@router.post("/edit/{course_id}")
async def edit_course(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    status_str: str = Form("draft"),
    subject: str = Form("Other"),
    grade_level: int = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    await course_service.update_course(
        db, user_id, course_id,
        course_name, description, credit_hours, status_str, subject, grade_level, thumbnail
    )
    return RedirectResponse(url="/teacher/courses/list", status_code=303)

# =====================================================
# ❌ Xóa khóa học
# =====================================================
@router.post("/delete/{course_id}")
def delete_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    ok = course_service.delete_course(db, user_id, course_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy hoặc không có quyền xóa khóa học.")
    return RedirectResponse(url="/teacher/courses/list", status_code=303)

# =====================================================
# 📘 Chi tiết khóa học
# =====================================================
@router.get("/detail/{course_id}", response_class=HTMLResponse)
def course_detail(course_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị chi tiết khóa học cho giáo viên"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    # ✅ Kiểm tra đăng nhập
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    # ✅ Lấy khóa học theo ID
    course = db.query(Course).filter(
        Course.id == course_id, Course.teacher_id == user_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền truy cập.")

    # ✅ Lấy module & bài học
    modules = db.query(Module).filter(Module.course_id == course.id).all()
    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(Module.course_id == course.id)
        .all()
    )

    return templates.TemplateResponse(
        "teacher/courses/detail.html",
        {
            "request": request,
            "course": course,
            "modules": modules,
            "lessons": lessons,
            "now": datetime.now(),
        },
    )

# =====================================================
# 🧩 Quản lý khóa học & bài học (gộp thẻ)
# =====================================================
@router.get("/manage", response_class=HTMLResponse)
def manage_courses(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả khóa học cùng module & bài học"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    teacher = db.query(User).filter(User.id == user_id).first()

    courses = (
        db.query(Course)
        .filter(Course.teacher_id == user_id)
        .order_by(Course.created_at.desc())
        .all()
    )

    # ✅ Gộp module & lesson vào từng course
    data = []
    for c in courses:
        modules = (
            db.query(Module)
            .filter(Module.course_id == c.id)
            .order_by(Module.module_number.asc())
            .all()
        )
        for m in modules:
            lessons = (
                db.query(Lesson)
                .filter(Lesson.module_id == m.id)
                .order_by(Lesson.lesson_number.asc())
                .all()
            )
            m.lessons = lessons
        c.modules = modules
        data.append(c)

    return templates.TemplateResponse(
        "teacher/courses/manage.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": data,
            "now": datetime.now(),
        },
    )
@router.get("/detail/{course_id}", response_class=HTMLResponse)
async def course_detail(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    Trang chi tiết khóa học, hiển thị danh sách module & bài học.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return HTMLResponse("<h3>Không tìm thấy khóa học.</h3>", status_code=404)

    modules = (
        db.query(Module)
        .filter(Module.course_id == course_id)
        .order_by(Module.module_number.asc())
        .all()
    )

    # Load danh sách bài học theo module
    for m in modules:
        m.lessons = (
            db.query(Lesson)
            .filter(Lesson.module_id == m.id)
            .order_by(Lesson.lesson_number.asc())
            .all()
        )

    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "course": course,
            "modules": modules
        }
    )
