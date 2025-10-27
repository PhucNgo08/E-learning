from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import teacher_service

# ✅ Import hệ thống template chung
from app.config.template_config import get_template_by_path


# ============================================================
# 🚀 Router
# ============================================================
router = APIRouter(
    prefix="/admin/teachers",
    tags=["Admin - Teacher Management"]
)

# ============================================================
# 📋 Danh sách giáo viên
# ============================================================
@router.get("/list", response_class=HTMLResponse)
def list_teachers(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    teachers = teacher_service.get_all_teachers(db)
    return tpl.TemplateResponse(
        "teacher/list.html",
        {"request": request, "teachers": teachers, "page_title": "👩‍🏫 Danh sách giáo viên"}
    )

# ============================================================
# ➕ Form tạo giáo viên
# ============================================================
@router.get("/create", response_class=HTMLResponse)
def create_teacher_form(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("teacher/create.html", {"request": request, "page_title": "➕ Thêm giáo viên"})

# ============================================================
# 💾 Xử lý tạo giáo viên
# ============================================================
@router.post("/create")
def create_teacher(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("teacher"),
    db: Session = Depends(get_db)
):
    teacher_service.create_teacher(db, username, email, full_name, role)
    return RedirectResponse(url="/admin/teachers/list", status_code=303)

# ============================================================
# ✏️ Chỉnh sửa giáo viên
# ============================================================
@router.get("/edit/{teacher_id}", response_class=HTMLResponse)
def edit_teacher(request: Request, teacher_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    teacher = teacher_service.get_teacher(db, teacher_id)
    return tpl.TemplateResponse(
        "teacher/edit.html",
        {"request": request, "teacher": teacher, "page_title": "✏️ Chỉnh sửa giáo viên"}
    )


@router.post("/edit/{teacher_id}")
def update_teacher(
    request: Request,
    teacher_id: str,
    full_name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    teacher_service.update_teacher(db, teacher_id, full_name, email, role)
    return RedirectResponse(url="/admin/teachers/list", status_code=303)
