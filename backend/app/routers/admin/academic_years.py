from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import academic_year_service
from pathlib import Path
from app.models.user import User
from app.models.academic_year import AcademicYear
from datetime import datetime
import traceback

# ==============================
# 🧭 Cấu hình template
# ==============================
# ✅ Trỏ đến thư mục gốc templates để có thể extends layout_admin.html
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ==============================
# 🚀 Khởi tạo router
# ==============================
router = APIRouter(
    prefix="/admin/academic_years",
    tags=["Admin - Academic Years Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách năm học
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def list_academic_years(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách năm học trong hệ thống."""
    try:
        years = academic_year_service.get_all_academic_years(db)
        return templates.TemplateResponse(
            "admin/academic_years/list.html",
            {"request": request, "years": years, "current_year": datetime.now().year}
        )
    except Exception:
        print("\n❌ LỖI DANH SÁCH NĂM HỌC:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# ➕ 2️⃣ Tạo năm học mới
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_form(request: Request):
    """Hiển thị form tạo năm học mới."""
    return templates.TemplateResponse(
        "admin/academic_years/create.html",
        {"request": request, "current_year": datetime.now().year}
    )


@router.post("/create", response_class=HTMLResponse)
def create_academic_year(
    request: Request,
    year_code: str = Form(...),
    year_name: str = Form(...),
    start_year: int = Form(...),
    end_year: int = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Xử lý thêm năm học mới."""
    try:
        academic_year_service.create_academic_year(
            db, year_code, year_name, start_year, end_year, is_active
        )
        print("✅ Tạo năm học mới thành công:", year_name)
        return RedirectResponse(
            url="/admin/academic_years/list",
            status_code=303
        )
    except ValueError as e:
        # ⚠️ Hiển thị lỗi thân thiện (ví dụ trùng mã)
        return templates.TemplateResponse(
            "admin/academic_years/create.html",
            {
                "request": request,
                "error": str(e),
                "current_year": datetime.now().year
            },
            status_code=400
        )
    except Exception:
        print("\n❌ LỖI TẠO NĂM HỌC:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# ✏️ 3️⃣ Chỉnh sửa năm học
# =========================================================
@router.get("/edit/{year_id}", response_class=HTMLResponse)
def edit_form(request: Request, year_id: str, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa năm học."""
    year = academic_year_service.get_academic_year_by_id(db, year_id)
    if not year:
        raise HTTPException(status_code=404, detail="Không tìm thấy năm học.")
    return templates.TemplateResponse(
        "admin/academic_years/edit.html",
        {"request": request, "year": year, "current_year": datetime.now().year}
    )


@router.post("/edit/{year_id}", response_class=HTMLResponse)
def update_academic_year(
    request: Request,
    year_id: str,
    year_code: str = Form(...),
    year_name: str = Form(...),
    start_year: int = Form(...),
    end_year: int = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin năm học."""
    try:
        academic_year_service.update_academic_year(
            db,
            year_id,
            {
                "year_code": year_code,
                "year_name": year_name,
                "start_year": start_year,
                "end_year": end_year,
                "is_active": 1 if is_active else 0
            }
        )
        print("✅ Cập nhật năm học:", year_name)
        return RedirectResponse(
            url="/admin/academic_years/list",
            status_code=303
        )
    except ValueError as e:
        year = academic_year_service.get_academic_year_by_id(db, year_id)
        return templates.TemplateResponse(
            "admin/academic_years/edit.html",
            {
                "request": request,
                "year": year,
                "error": str(e),
                "current_year": datetime.now().year
            },
            status_code=400
        )
    except Exception:
        print("\n❌ LỖI CẬP NHẬT NĂM HỌC:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 🗑️ 4️⃣ Xóa năm học
# =========================================================
@router.get("/delete/{year_id}")
def delete_academic_year(year_id: str, db: Session = Depends(get_db)):
    """Xóa năm học khỏi hệ thống."""
    try:
        result = academic_year_service.delete_academic_year(db, year_id)
        if not result:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học cần xóa.")
        print("🗑️ Đã xóa năm học có ID:", year_id)
        return RedirectResponse(
            url="/admin/academic_years/list",
            status_code=303
        )
    except Exception:
        print("\n❌ LỖI XÓA NĂM HỌC:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 👥 5️⃣ Xem danh sách sinh viên theo năm học
# =========================================================
@router.get("/{year_id}/students", response_class=HTMLResponse)
def students_by_year(request: Request, year_id: str, db: Session = Depends(get_db)):
    """Hiển thị danh sách sinh viên thuộc năm học cụ thể."""
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học.")

        students = db.query(User).filter(
            User.academic_year_id == year_id,
            User.role == "student"
        ).all()

        print(f"👥 Năm học: {year.year_name} — Số sinh viên: {len(students)}")

        return templates.TemplateResponse(
            "admin/academic_years/students_by_year.html",
            {
                "request": request,
                "year": year,
                "students": students,
                "current_year": datetime.now().year
            }
        )
    except Exception:
        print("\n❌ LỖI HIỂN THỊ SINH VIÊN THEO NĂM HỌC:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
