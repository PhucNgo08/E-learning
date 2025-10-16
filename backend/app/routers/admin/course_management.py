from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.course import Course
from app.models.user import User
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.database.connection import get_db

# ============================================================
# ⚙️ Router cấu hình
# ============================================================
course_router = APIRouter(prefix="/admin/Course", tags=["Admin - Course Management"])
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ============================================================
# 🧩 1️⃣ Trang quản lý khóa học
# ============================================================
@course_router.get("/manage", response_class=HTMLResponse)
async def manage_courses(request: Request, db: Session = Depends(get_db)):
    courses = (
        db.query(Course)
        .order_by(Course.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "admin/Course/manage.html",
        {"request": request, "courses": courses, "active_page": "course"}
    )

# ============================================================
# ➕ 2️⃣ Trang thêm khóa học mới (GET)
# ============================================================
@course_router.get("/create", response_class=HTMLResponse)
async def create_course_page(request: Request, db: Session = Depends(get_db)):
    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return templates.TemplateResponse(
        "admin/Course/create.html",
        {
            "request": request,
            "teachers": teachers,
            "years": years,
            "majors": majors,
            "active_page": "course"
        }
    )

# ➕ 2️⃣ Thêm khóa học mới (POST)
@course_router.post("/add")
async def add_course(
    course_code: str = Form(...),
    course_name: str = Form(...),
    description: str = Form(None),
    credit_hours: int = Form(...),
    teacher_id: str = Form(None),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        new_course = Course(
            id=str(uuid4()),
            course_code=course_code,
            course_name=course_name,
            description=description,
            credit_hours=credit_hours,
            teacher_id=teacher_id,
            academic_year_id=academic_year_id,
            major_id=major_id,
            status="draft",
        )

        # Xử lý ngày bắt đầu / kết thúc (nếu có)
        if start_date:
            new_course.start_date = start_date
        if end_date:
            new_course.end_date = end_date

        db.add(new_course)
        db.commit()
        db.refresh(new_course)

        return RedirectResponse(url="/admin/Course/manage", status_code=303)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm khóa học: {e}")

# ============================================================
# ✏️ 3️⃣ Trang chỉnh sửa khóa học (GET)
# ============================================================
@course_router.get("/edit/{course_id}", response_class=HTMLResponse)
async def edit_course_page(course_id: str, request: Request, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Khóa học không tồn tại")

    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return templates.TemplateResponse(
        "admin/Course/edit.html",
        {
            "request": request,
            "course": course,
            "teachers": teachers,
            "years": years,
            "majors": majors,
            "active_page": "course"
        }
    )

# ✏️ 3️⃣ Cập nhật khóa học (POST)
@course_router.post("/edit/{course_id}")
async def edit_course_action(
    course_id: str,
    course_code: str = Form(...),
    course_name: str = Form(...),
    description: str = Form(None),
    credit_hours: int = Form(...),
    teacher_id: str = Form(None),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    start_date: str = Form(None),
    end_date: str = Form(None),
    status: str = Form("draft"),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Khóa học không tồn tại")

    course.course_code = course_code
    course.course_name = course_name
    course.description = description
    course.credit_hours = credit_hours
    course.teacher_id = teacher_id
    course.academic_year_id = academic_year_id
    course.major_id = major_id
    course.status = status

    if start_date:
        course.start_date = start_date
    if end_date:
        course.end_date = end_date

    db.commit()
    db.refresh(course)
    return RedirectResponse(url="/admin/Course/manage", status_code=303)

# ============================================================
# ❌ 4️⃣ Xóa khóa học
# ============================================================
@course_router.get("/delete/{course_id}")
async def delete_course(course_id: str, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Khóa học không tồn tại")

    db.delete(course)
    db.commit()
    return RedirectResponse(url="/admin/Course/manage", status_code=303)
