from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.classes import Class
from datetime import datetime
import uuid

# === Cấu hình router & template ===
enrollment_router = APIRouter(prefix="/admin/enrollments", tags=["Admin - Enrollment Management"])
templates = Jinja2Templates(directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/enrollments")

# ============================================================
# 📋 1️⃣ Danh sách ghi danh
# ============================================================
@enrollment_router.get("/manage", response_class=HTMLResponse)
def manage_enrollments(request: Request, db: Session = Depends(get_db)):
    enrollments = db.query(Enrollment).all()
    return templates.TemplateResponse(
        "manage.html",
        {"request": request, "enrollments": enrollments}
    )


# ============================================================
# ➕ 2️⃣ Form thêm ghi danh
# ============================================================
@enrollment_router.get("/create", response_class=HTMLResponse)
def create_enrollment_form(request: Request, db: Session = Depends(get_db)):
    students = db.query(User).filter(User.role == "student").all()
    classes = db.query(Class).all()
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "students": students, "classes": classes}
    )


# ============================================================
# 💾 3️⃣ Xử lý thêm ghi danh
# ============================================================
@enrollment_router.post("/create")
def add_enrollment(
    user_id: str = Form(...),
    class_id: str = Form(...),
    enrollment_type: str = Form("official"),
    db: Session = Depends(get_db)
):
    try:
        existing = db.query(Enrollment).filter(Enrollment.user_id == user_id, Enrollment.class_id == class_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Học viên đã được ghi danh vào lớp này.")
        new_enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            class_id=class_id,
            enrollment_type=enrollment_type,
            enrollment_status="applied",
            applied_at=datetime.utcnow()
        )
        db.add(new_enrollment)
        db.commit()
        return RedirectResponse(url="/admin/enrollments/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi ghi danh: {str(e)}")


# ============================================================
# ✏️ 4️⃣ Cập nhật trạng thái ghi danh
# ============================================================
@enrollment_router.post("/update/{enrollment_id}")
def update_enrollment(enrollment_id: str, new_status: str = Form(...), db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi danh.")
    try:
        enrollment.enrollment_status = new_status
        enrollment.updated_at = datetime.utcnow()
        db.commit()
        return RedirectResponse(url="/admin/enrollments/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật: {str(e)}")


# ============================================================
# ❌ 5️⃣ Xóa ghi danh
# ============================================================
@enrollment_router.get("/delete/{enrollment_id}")
def delete_enrollment(enrollment_id: str, db: Session = Depends(get_db)):
    enrollment = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Không tìm thấy ghi danh.")
    try:
        db.delete(enrollment)
        db.commit()
        return RedirectResponse(url="/admin/enrollments/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa ghi danh: {str(e)}")
