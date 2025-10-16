# ==============================================================
# 📘 ROUTER: Quản lý học phần (Course Sections)
# ==============================================================

from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.course_section_service import (
    create_section,
    update_section,
    delete_section,
    get_all_sections,
)
from app.models.course import Course
from app.models.course_section import CourseSection

# ==============================================================
# ⚙️ Router & Templates
# ==============================================================
section_router = APIRouter(prefix="/admin", tags=["Course Section Management"])

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/Sections"
)

# ==============================================================
# 📋 Danh sách học phần
# ==============================================================
@section_router.get("/sections/manage", response_class=HTMLResponse)
async def manage_sections(request: Request, db: Session = Depends(get_db)):
    sections = get_all_sections(db)
    return templates.TemplateResponse(
        "manage.html",
        {"request": request, "sections": sections},
    )

# ==============================================================
# ➕ Form thêm học phần (GET)
# ==============================================================
@section_router.get("/sections/create", response_class=HTMLResponse)
async def create_section_form(request: Request, db: Session = Depends(get_db)):
    courses = db.query(Course).all()
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "courses": courses},
    )

# ==============================================================
# 💾 Xử lý thêm học phần (POST)
# ==============================================================
@section_router.post("/sections/create")
async def add_section(
    section_code: str = Form(...),
    section_name: str = Form(...),
    course_id: str = Form(...),
    max_students: int = Form(50),
    location: str = Form(""),
    schedule_info: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        new_section = create_section(
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            location=location,
            schedule_info=schedule_info,
            db=db,
        )
        return RedirectResponse(url="/admin/sections/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo học phần: {e}")

# ==============================================================
# ✏️ Form chỉnh sửa học phần
# ==============================================================
@section_router.get("/sections/edit/{section_id}", response_class=HTMLResponse)
async def edit_section_form(request: Request, section_id: str, db: Session = Depends(get_db)):
    section = db.query(CourseSection).filter(CourseSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Không tìm thấy học phần.")
    courses = db.query(Course).all()
    return templates.TemplateResponse(
        "edit.html",
        {"request": request, "section": section, "courses": courses},
    )

# ==============================================================
# 🔄 Xử lý cập nhật học phần (POST)
# ==============================================================
@section_router.post("/sections/edit/{section_id}")
async def edit_section(
    section_id: str,
    section_code: str = Form(...),
    section_name: str = Form(...),
    course_id: str = Form(...),
    max_students: int = Form(50),
    location: str = Form(""),
    schedule_info: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        update_section(
            section_id=section_id,
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            location=location,
            schedule_info=schedule_info,
            db=db,
        )
        return RedirectResponse(url="/admin/sections/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật học phần: {e}")

# ==============================================================
# ❌ Xóa học phần
# ==============================================================
@section_router.get("/sections/delete/{section_id}")
async def delete_section_route(section_id: str, db: Session = Depends(get_db)):
    try:
        delete_section(section_id, db)
        return RedirectResponse(url="/admin/sections/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa học phần: {e}")
