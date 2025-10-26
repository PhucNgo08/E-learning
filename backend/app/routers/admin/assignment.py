from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import (
    HTMLResponse, RedirectResponse, FileResponse
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from pathlib import Path
import traceback
import os
from app.models.user import User

# ==============================
# 🧩 Import database & services
# ==============================
from app.database.connection import get_db
from app.services.admin.assignment_service import (
    get_all,
    get_by_id,
    create_assignment,
    update_assignment,
    delete_assignment,
    get_global_assignment_report,
    get_teacher_assignment_stats,
    get_student_assignment_summary,
)
from app.services.admin.assignment_analytics_service import (
    get_assignment_analytics,
    export_assignment_scores_to_excel,
)

# ==============================
# 🧭 Template Configuration
# ==============================
# ⚙️ Sửa lại: trỏ đến thư mục templates gốc để có thể extends layout_admin.html
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ==============================
# 🚀 Router
# ==============================
router = APIRouter(
    prefix="/admin/assignment",
    tags=["Admin - Assignment Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách bài tập
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def assignment_list(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách bài tập."""
    try:
        assignments = get_all(db)
        stats = get_global_assignment_report(db)
        return templates.TemplateResponse(
            "admin/assignment/list.html",
            {
                "request": request,
                "assignments": assignments,
                "stats": stats,
                "current_year": datetime.now().year,
            },
        )
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(f"<pre>Lỗi khi tải danh sách: {e}</pre>", status_code=500)

# =========================================================
# ➕ 2️⃣ Tạo bài tập mới
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_assignment_form(request: Request):
    """Hiển thị form tạo bài tập."""
    return templates.TemplateResponse(
        "admin/assignment/create.html",
        {"request": request, "current_year": datetime.now().year}
    )


@router.post("/create")
def create_assignment_route(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(...),
    due_date: str = Form(None),
    db: Session = Depends(get_db)
):
    """Xử lý POST tạo bài tập mới."""
    try:
        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = datetime.fromisoformat(due_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Định dạng ngày không hợp lệ (YYYY-MM-DD).")

        create_assignment(db, title, description, course_id, parsed_due_date)
        print(f"✅ [Tạo bài tập] {title}")
        return RedirectResponse(url="/admin/assignment/list", status_code=303)
    except Exception as e:
        db.rollback()
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# ✏️ 3️⃣ Chỉnh sửa bài tập
# =========================================================
@router.get("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_form(assignment_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa bài tập."""
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")
    return templates.TemplateResponse(
        "admin/assignment/edit.html",
        {"request": request, "assignment": assignment, "current_year": datetime.now().year},
    )


@router.post("/edit/{assignment_id}")
def edit_assignment_route(
    assignment_id: str,
    title: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    """Xử lý cập nhật bài tập."""
    try:
        updated = update_assignment(db, assignment_id, title, description)
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập để cập nhật.")
        print(f"✏️ [Cập nhật bài tập] {title}")
        return RedirectResponse(url="/admin/assignment/list", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 🗑️ 4️⃣ Xóa bài tập
# =========================================================
@router.get("/delete/{assignment_id}", response_class=HTMLResponse)
def confirm_delete(assignment_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị trang xác nhận xóa."""
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")
    return templates.TemplateResponse(
        "admin/assignment/delete.html",
        {"request": request, "assignment": assignment, "current_year": datetime.now().year},
    )


@router.post("/delete/{assignment_id}")
def delete_assignment_route(assignment_id: str, db: Session = Depends(get_db)):
    """Xử lý xóa bài tập."""
    try:
        result = delete_assignment(db, assignment_id)
        if not result:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập để xóa.")
        print(f"🗑️ [Xóa bài tập] ID: {assignment_id}")
        return RedirectResponse(url="/admin/assignment/list", status_code=303)
    except Exception as e:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 📊 5️⃣ Quản lý theo khóa học
# =========================================================
@router.get("/manage/{course_id}", response_class=HTMLResponse)
def manage_assignments(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị thống kê bài tập trong một khóa học."""
    try:
        stats = get_assignment_analytics(db, course_id)
        return templates.TemplateResponse(
            "admin/assignment/manage.html",
            {"request": request, "stats": stats, "course_id": course_id},
        )
    except Exception as e:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 📈 6️⃣ Trang thống kê tổng hợp (Dashboard)
# =========================================================
@router.get("/stats", response_class=HTMLResponse)
def assignment_stats_dashboard(request: Request, db: Session = Depends(get_db)):
    """Hiển thị dashboard thống kê bài tập toàn hệ thống."""
    try:
        global_stats = get_global_assignment_report(db)
        teacher_stats = []
        student_stats = []

        # Lấy thống kê giáo viên
        teachers = db.query(User).filter(User.role == "teacher").all()
        for t in teachers:
            teacher_stats.append({
                "teacher_name": t.full_name,
                "data": get_teacher_assignment_stats(db, t.id)
            })

        # Lấy thống kê 5 sinh viên gần nhất
        students = db.query(User).filter(User.role == "student").limit(5).all()
        for s in students:
            student_stats.append({
                "student_name": s.full_name,
                "data": get_student_assignment_summary(db, s.id)
            })

        return templates.TemplateResponse(
            "admin/assignment/stats.html",
            {
                "request": request,
                "global_stats": global_stats,
                "teacher_stats": teacher_stats,
                "student_stats": student_stats,
                "current_year": datetime.now().year,
            },
        )
    except Exception as e:
        print("❌ Lỗi khi tải thống kê tổng hợp:", e)
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# 📤 7️⃣ Xuất Excel
# =========================================================
@router.get("/export_excel/{assignment_id}")
def export_assignment_excel(assignment_id: str, db: Session = Depends(get_db)):
    """Xuất kết quả bài tập ra file Excel."""
    try:
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        file_path = export_dir / f"assignment_{assignment_id}.xlsx"

        export_assignment_scores_to_excel(db, assignment_id, str(file_path))
        print(f"📤 [Xuất Excel] {file_path.name}")

        return FileResponse(
            str(file_path),
            filename=file_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        print("❌ Lỗi xuất Excel:", e)
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
