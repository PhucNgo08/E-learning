from fastapi import APIRouter, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import teacher_service

from app.config.template_config import get_template_by_path


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
        {
            "request": request,
            "teachers": teachers,
            "page_title": "👩‍🏫 Danh sách giáo viên"
        }
    )


# ============================================================
# ➕ Form tạo giáo viên
# ============================================================
@router.get("/create", response_class=HTMLResponse)
def create_teacher_form(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "teacher/create.html",
        {
            "request": request,
            "page_title": "➕ Thêm giáo viên",
            "roles": ["teacher", "teaching_assistant"]
        }
    )


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
# ✏️ Form sửa giáo viên
# ============================================================
@router.get("/edit/{teacher_id}", response_class=HTMLResponse)
def edit_teacher(request: Request, teacher_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    teacher = teacher_service.get_teacher(db, teacher_id)

    return tpl.TemplateResponse(
        "teacher/edit.html",
        {
            "request": request,
            "teacher": teacher,
            "roles": ["teacher", "teaching_assistant"],
            "page_title": "✏️ Chỉnh sửa giáo viên"
        }
    )


# ============================================================
# 💾 Xử lý cập nhật giáo viên
# ============================================================
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


# ============================================================
# 🖼️ Form upload avatar
# ============================================================
@router.get("/avatar/{teacher_id}", response_class=HTMLResponse)
def edit_avatar(request: Request, teacher_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    teacher = teacher_service.get_teacher(db, teacher_id)
    return tpl.TemplateResponse(
        "teacher/edit_avatar.html",
        {
            "request": request,
            "teacher": teacher,
            "page_title": "🖼️ Cập nhật Avatar"
        }
    )


# ============================================================
# 📤 Upload avatar cho giáo viên
# ============================================================
@router.post("/avatar/{teacher_id}")
def upload_avatar(
    request: Request,
    teacher_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    teacher_service.update_teacher_avatar(db, teacher_id, file)
    return RedirectResponse(url=f"/admin/teachers/edit/{teacher_id}", status_code=303)


# ============================================================
# 🔐 Reset mật khẩu
# ============================================================
@router.get("/reset-password/{teacher_id}", response_class=HTMLResponse)
def reset_password(request: Request, teacher_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)

    teacher, new_pwd = teacher_service.reset_teacher_password(db, teacher_id)

    return tpl.TemplateResponse(
        "teacher/reset_password.html",
        {
            "request": request,
            "teacher": teacher,
            "new_password": new_pwd,
            "page_title": "🔐 Mật khẩu mới"
        }
    )
