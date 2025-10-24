from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.schemas.UserCreate import UserCreate
from app.services.admin import teacher_service
from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/teacher"
)


router = APIRouter(
    prefix="/admin/teachers",
    tags=["Admin - Teacher Management"]
)

@router.get("/list", response_class=HTMLResponse)
def list_teachers(request: Request, db: Session = Depends(get_db)):
    teachers = teacher_service.get_all_teachers(db)
    return templates.TemplateResponse("list.html", {"request": request, "teachers": teachers})

@router.get("/create", response_class=HTMLResponse)
def create_teacher_form(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

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

@router.get("/edit/{teacher_id}", response_class=HTMLResponse)
def edit_teacher(request: Request, teacher_id: str, db: Session = Depends(get_db)):
    teacher = teacher_service.get_teacher(db, teacher_id)
    return templates.TemplateResponse("edit.html", {"request": request, "teacher": teacher})

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
