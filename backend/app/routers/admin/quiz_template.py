from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import quiz_template_service

# Template config dùng chung
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/admin/quiz-template",
    tags=["Admin - Quiz Template Management"]
)

# ============================================================
# 📋 Danh sách Templates
# ============================================================
@router.get("/list", response_class=HTMLResponse)
def list_templates(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    templates_list = quiz_template_service.get_all(db)
    return tpl.TemplateResponse(
        "quiz_template/list.html",
        {"request": request, "templates": templates_list}
    )

# ============================================================
# ➕ Form tạo mới
# ============================================================
@router.get("/create", response_class=HTMLResponse)
def create_form(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse("quiz_template/create.html", {"request": request})

# ============================================================
# ➕ Xử lý tạo mới (FIXED: Created_by)
# ============================================================
@router.post("/create")
def create(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    rules: str = Form(...),
    db: Session = Depends(get_db)
):
    # 🔥 Lấy user hiện tại từ session
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(status_code=403, detail="Bạn chưa đăng nhập.")

    # 🔥 Gọi service với created_by
    quiz_template_service.create(db, name, description, rules, created_by=user_id)

    return RedirectResponse(url="/admin/quiz-template/list", status_code=303)

# ============================================================
# ✏️ Form sửa Template
# ============================================================
@router.get("/edit/{template_id}", response_class=HTMLResponse)
def edit_form(template_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    qt = quiz_template_service.get_by_id(db, template_id)
    return tpl.TemplateResponse(
        "quiz_template/edit.html",
        {"request": request, "template": qt}
    )

# ============================================================
# ✏️ Xử lý sửa Template
# ============================================================
@router.post("/edit/{template_id}")
def update_template(
    template_id: str,
    name: str = Form(...),
    description: str = Form(None),
    rules: str = Form(...),
    db: Session = Depends(get_db)
):
    quiz_template_service.update(db, template_id, name, description, rules)
    return RedirectResponse(url="/admin/quiz-template/list", status_code=303)

# ============================================================
# 🗑️ Xác nhận xóa
# ============================================================
@router.get("/delete/{template_id}", response_class=HTMLResponse)
def confirm_delete(template_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    qt = quiz_template_service.get_by_id(db, template_id)
    return tpl.TemplateResponse(
        "quiz_template/delete.html",
        {"request": request, "template": qt}
    )

# ============================================================
# 🗑️ Xử lý xóa
# ============================================================
@router.post("/delete/{template_id}")
def delete(template_id: str, db: Session = Depends(get_db)):
    quiz_template_service.delete(db, template_id)
    return RedirectResponse(url="/admin/quiz-template/list", status_code=303)
