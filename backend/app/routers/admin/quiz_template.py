from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import quiz_template_service


templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/quiz_template"
)
router = APIRouter(
    prefix="/admin/quiz-template",
    tags=["Admin - Quiz Template Management"]
)

# 📋 Danh sách
@router.get("/list", response_class=HTMLResponse)
def list_templates(request: Request, db: Session = Depends(get_db)):
    templates_list = quiz_template_service.get_all(db)
    return templates.TemplateResponse("list.html", {"request": request, "templates": templates_list})

# ➕ Tạo
@router.get("/create", response_class=HTMLResponse)
def create_form(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@router.post("/create")
def create(
    name: str = Form(...),
    description: str = Form(None),
    rules: str = Form(...),
    db: Session = Depends(get_db)
):
    quiz_template_service.create(db, name, description, rules)
    return RedirectResponse(url="/admin/quiz-template/list", status_code=303)

# ✏️ Sửa
@router.get("/edit/{template_id}", response_class=HTMLResponse)
def edit_form(template_id: str, request: Request, db: Session = Depends(get_db)):
    qt = quiz_template_service.get_by_id(db, template_id)
    return templates.TemplateResponse("edit.html", {"request": request, "template": qt})

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

# 🗑️ Xóa
@router.get("/delete/{template_id}", response_class=HTMLResponse)
def confirm_delete(template_id: str, request: Request, db: Session = Depends(get_db)):
    qt = quiz_template_service.get_by_id(db, template_id)
    return templates.TemplateResponse("delete.html", {"request": request, "template": qt})

@router.post("/delete/{template_id}")
def delete(template_id: str, db: Session = Depends(get_db)):
    quiz_template_service.delete(db, template_id)
    return RedirectResponse(url="/admin/quiz-template/list", status_code=303)
