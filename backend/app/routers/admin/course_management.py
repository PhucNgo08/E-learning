from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major

from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.database.connection import get_db
from app.services import course_service
from app.models.course import Course
from app.models.user import User

# =====================================================
# 🧭 Template Config
# =====================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/Course"
)

# =====================================================
# 🚀 Router (đặt tên đồng bộ với hệ thống)
# =====================================================
course_router = APIRouter(
    prefix="/admin/Course",
    tags=["Admin - Course Management"]
)

# =====================================================
# 📋 1️⃣ Danh sách khóa học
# =====================================================
@course_router.get("/manage", response_class=HTMLResponse)
async def manage_courses(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tất cả khóa học trong hệ thống."""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    courses = course_service.get_all_courses(db, user_id, "admin")

    return templates.TemplateResponse(
        "manage.html",
        {
            "request": request,
            "courses": courses,
            "active_page": "course",
            "now": datetime.now(),
        },
    )


# =====================================================
# ➕ 2️⃣ Trang tạo khóa học (GET)
# =====================================================
@course_router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, db: Session = Depends(get_db)):
    """Trang thêm khóa học mới."""
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return templates.TemplateResponse(
        "create.html",
        {
            "request": request,
            "teachers": teachers,
            "years": years,
            "majors": majors,
            "active_page": "course",
        },
    )


# =====================================================
# 💾 3️⃣ Xử lý tạo khóa học (POST)
# =====================================================
@course_router.post("/create")
async def create_course(
    request: Request,
    db: Session = Depends(get_db),
    course_name: str = Form(...),
    description: str = Form(""),
    credit_hours: int = Form(3),
    subject: str = Form("Other"),
    grade_level: int | None = Form(None),
    teacher_id: str | None = Form(None),
    academic_year_id: str | None = Form(None),
    major_id: str | None = Form(None),
    start_date: str | None = Form(None),
    end_date: str | None = Form(None),
    thumbnail: UploadFile | None = File(None),
):
    """Thêm khóa học mới (Admin có thể chọn giáo viên)."""
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await course_service.create_course(
        db, teacher_id or "", course_name, description,
        credit_hours, subject, grade_level, thumbnail,
        role="admin"
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(url="/admin/Course/manage", status_code=303)


# =====================================================
# ✏️ 4️⃣ Trang chỉnh sửa khóa học (GET)
# =====================================================
@course_router.get("/edit/{course_id}", response_class=HTMLResponse)
async def page_edit(course_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa khóa học."""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    course = course_service.get_course_owned(db, user_id, course_id, role="admin")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "course": course,
            "teachers": teachers,
            "years": years,
            "majors": majors,
            "active_page": "course",
        },
    )


# =====================================================
# 💾 5️⃣ Cập nhật khóa học (POST)
# =====================================================
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
    thumbnail: UploadFile | None = File(None),
):
    """Cập nhật thông tin khóa học (admin)."""
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await course_service.update_course(
        db, teacher_id or "", course_id,
        course_name, description, credit_hours,
        status_str, subject, grade_level, thumbnail,
        role="admin"
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return RedirectResponse(url="/admin/Course/manage", status_code=303)


# =====================================================
# ❌ 6️⃣ Xóa khóa học
# =====================================================
@course_router.post("/delete/{course_id}")
async def delete_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    """Xóa khóa học (admin)."""
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    ok = course_service.delete_course(db, user_id, course_id, role="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Không thể xóa khóa học.")

    return RedirectResponse(url="/admin/Course/manage", status_code=303)


# =====================================================
# 📘 7️⃣ Xem chi tiết khóa học
# =====================================================
@course_router.get("/detail/{course_id}", response_class=HTMLResponse)
async def course_detail(course_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị chi tiết khóa học."""
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    teacher = db.query(User).filter(User.id == course.teacher_id).first()
    return templates.TemplateResponse(
        "detail.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "active_page": "course",
            "now": datetime.now(),
        },
    )
