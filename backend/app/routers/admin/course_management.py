from fastapi import (
    APIRouter, Request, Depends, Form, UploadFile, File, HTTPException, Query
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.course import Course
from app.models.user import User
from app.services import course_service

# ✅ Import template config dùng chung
from app.config.template_config import get_template_by_path

# =====================================================
# 🚀 Router (Admin - Course Management)
# =====================================================
course_router = APIRouter(
    prefix="/admin/Course",
    tags=["Admin - Course Management"]
)

# =====================================================
# 📋 1️⃣ Danh sách khóa học (có lọc + phân trang)
# =====================================================
@course_router.get("/manage", response_class=HTMLResponse)
async def manage_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str = Query(None, description="Từ khóa tìm kiếm"),
    status: str = Query(None),
    teacher_id: str = Query(None),
    major_id: str = Query(None),
    year_id: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = 10
):
    """Hiển thị danh sách khóa học có hỗ trợ lọc và phân trang."""
    tpl = get_template_by_path(request.url.path)
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    query = db.query(Course).join(User, Course.teacher_id == User.id, isouter=True)

    if q:
        query = query.filter(
            (Course.course_name.ilike(f"%{q}%")) |
            (Course.course_code.ilike(f"%{q}%"))
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
    courses = query.order_by(Course.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    teachers = db.query(User).filter(User.role == "teacher").all()
    majors = db.query(Major).all()
    years = db.query(AcademicYear).all()

    return tpl.TemplateResponse(
        "Course/manage.html",
        {
            "request": request,
            "courses": courses,
            "teachers": teachers,
            "majors": majors,
            "years": years,
            "total": total,
            "current_page": page,
            "total_pages": total_pages,
            "q": q,
            "status": status,
            "teacher_id": teacher_id,
            "major_id": major_id,
            "year_id": year_id,
            "active_page": "course",
            "now": datetime.now(),
        },
    )

# =====================================================
# ➕ 2️⃣ Trang tạo khóa học
# =====================================================
@course_router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return tpl.TemplateResponse(
        "Course/create.html",
        {
            "request": request,
            "teachers": teachers,
            "years": years,
            "majors": majors,
            "active_page": "course",
        },
    )

# =====================================================
# 💾 3️⃣ Tạo khóa học (POST)
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
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await course_service.create_course(
        db=db,
        user_id=request.session.get("user_id"),
        course_name=course_name,
        description=description,
        credit_hours=credit_hours,
        subject=subject,
        grade_level=grade_level,
        thumbnail=thumbnail,
        role="admin",
        teacher_id=teacher_id or None,
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    teacher = db.query(User).filter(User.id == teacher_id).first()
    print(f"✅ [ADMIN] Tạo khóa học: {course_name} ({teacher.full_name if teacher else 'Chưa phân công'})")
    return RedirectResponse(url="/admin/Course/manage", status_code=303)

# =====================================================
# ✏️ 4️⃣ Chỉnh sửa khóa học
# =====================================================
@course_router.get("/edit/{course_id}", response_class=HTMLResponse)
async def page_edit(course_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    course = course_service.get_course_owned(db, request.session.get("user_id"), course_id, role="admin")
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    teachers = db.query(User).filter(User.role == "teacher").all()
    years = db.query(AcademicYear).all()
    majors = db.query(Major).all()

    return tpl.TemplateResponse(
        "Course/edit.html",
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
# 💾 5️⃣ Cập nhật khóa học
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
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    result = await course_service.update_course(
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
        teacher_id=teacher_id or None,
    )

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    print(f"✏️ [ADMIN] Cập nhật khóa học: {course_name}")
    return RedirectResponse(url="/admin/Course/manage", status_code=303)

# =====================================================
# ❌ 6️⃣ Xóa khóa học
# =====================================================
@course_router.post("/delete/{course_id}")
async def delete_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    ok = course_service.delete_course(db, request.session.get("user_id"), course_id, role="admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Không thể xóa khóa học.")
    print(f"🗑️ [ADMIN] Xóa khóa học ID: {course_id}")
    return RedirectResponse(url="/admin/Course/manage", status_code=303)

# =====================================================
# 📘 7️⃣ Xem chi tiết khóa học
# =====================================================
@course_router.get("/detail/{course_id}", response_class=HTMLResponse)
async def course_detail(course_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")
    teacher = db.query(User).filter(User.id == course.teacher_id).first()

    return tpl.TemplateResponse(
        "Course/detail.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "active_page": "course",
            "now": datetime.now(),
        },
    )

# =====================================================
# 📊 8️⃣ Tổng quan khóa học
# =====================================================
@course_router.get("/overview", response_class=HTMLResponse)
async def course_overview(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    if request.session.get("role") != "admin":
        return RedirectResponse(url="/auth/login", status_code=303)

    total_courses = db.query(Course).count()
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_students = db.query(User).filter(User.role == "student").count()
    latest_course = db.query(Course).order_by(Course.created_at.desc()).first()

    return tpl.TemplateResponse(
        "Course/overview.html",
        {
            "request": request,
            "course": latest_course,
            "total_courses": total_courses,
            "total_teachers": total_teachers,
            "total_students": total_students,
            "active_page": "course_overview",
        },
    )
