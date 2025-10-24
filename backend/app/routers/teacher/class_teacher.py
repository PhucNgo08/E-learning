from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.teacher import class_service
from pathlib import Path

# =========================================================
# 🧭 Cấu hình template (đặt đúng thư mục)
# =========================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/classes"
)

# =========================================================
# 🚀 Router
# =========================================================
router = APIRouter(
    prefix="/teacher/classes",
    tags=["Teacher - Class Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách lớp mà giáo viên phụ trách
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def class_list(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách lớp mà giáo viên phụ trách"""
    classes = class_service.get_teacher_classes(db)
    return templates.TemplateResponse(
        "list.html",
        {"request": request, "classes": classes}
    )

# =========================================================
# 👨‍🎓 2️⃣ Xem danh sách học viên trong lớp
# =========================================================
@router.get("/students/{class_id}", response_class=HTMLResponse)
def class_students(class_id: str, request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách sinh viên trong lớp"""
    class_info = class_service.get_class_info(db, class_id)
    if not class_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")
    
    students = class_service.get_students_in_class(db, class_id)
    return templates.TemplateResponse(
        "students.html",
        {"request": request, "students": students, "class_info": class_info}
    )
