from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Import services và models
from app.database.connection import get_db
from app.services import user_service
from app.models.academic_year import AcademicYear
from app.models.major import Major

# ==============================
# 📁 Cấu hình template
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/Account"
)

# ==============================
# 🚀 Khởi tạo router
# ==============================
user_router = APIRouter(
    prefix="/admin/Account",
    tags=["Admin - User Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách người dùng
# =========================================================
@user_router.get("/manage-users", response_class=HTMLResponse)
def manage_users(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tất cả người dùng"""
    users = user_service.get_all_users(db)
    return templates.TemplateResponse(
        "list_users.html",
        {
            "request": request,
            "users": users,
            "current_year": datetime.now().year
        }
    )

# =========================================================
# ➕ 2️⃣ Thêm người dùng mới
# =========================================================
@user_router.get("/add-user", response_class=HTMLResponse)
def add_user_form(request: Request, db: Session = Depends(get_db)):
    """Hiển thị form thêm người dùng mới"""
    academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
    majors = db.query(Major).order_by(Major.major_name).all()
    return templates.TemplateResponse(
        "add_user.html",
        {
            "request": request,
            "academic_years": academic_years,
            "majors": majors,
            "current_year": datetime.now().year
        }
    )

@user_router.post("/add-user")
def add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    db: Session = Depends(get_db),
):
    """Xử lý POST tạo người dùng"""
    try:
        # ✅ Cho phép tạo admin
        user_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            db=db,
            academic_year_id=academic_year_id,
            major_id=major_id
        )
        return RedirectResponse("/admin/Account/manage-users", status_code=303)
    except Exception as e:
        academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
        majors = db.query(Major).order_by(Major.major_name).all()
        return templates.TemplateResponse(
            "add_user.html",
            {
                "request": request,
                "error": str(e),
                "academic_years": academic_years,
                "majors": majors,
                "current_year": datetime.now().year
            },
            status_code=400
        )

# =========================================================
# ✏️ 3️⃣ Cập nhật thông tin người dùng
# =========================================================
@user_router.get("/edit-user/{user_id}", response_class=HTMLResponse)
def edit_user_form(request: Request, user_id: str, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa thông tin người dùng"""
    user = user_service.get_user_by_id(user_id, db)
    if not user:
        return HTMLResponse("Không tìm thấy người dùng.", status_code=404)

    academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
    majors = db.query(Major).order_by(Major.major_name).all()

    return templates.TemplateResponse(
        "edit_user.html",
        {
            "request": request,
            "user": user,
            "academic_years": academic_years,
            "majors": majors,
            "current_year": datetime.now().year
        }
    )

@user_router.post("/edit-user/{user_id}")
def edit_user(
    request: Request,
    user_id: str,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    full_name: str = Form(...),
    role: str = Form(...),
    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    db: Session = Depends(get_db),
):
    """Cập nhật thông tin người dùng"""
    try:
        user_service.update_user(
            user_id=user_id,
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            db=db,
            academic_year_id=academic_year_id,
            major_id=major_id
        )
        return RedirectResponse("/admin/Account/manage-users", status_code=303)
    except Exception as e:
        user = user_service.get_user_by_id(user_id, db)
        academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
        majors = db.query(Major).order_by(Major.major_name).all()
        return templates.TemplateResponse(
            "edit_user.html",
            {
                "request": request,
                "user": user,
                "error": str(e),
                "academic_years": academic_years,
                "majors": majors,
                "current_year": datetime.now().year
            },
            status_code=400
        )

# =========================================================
# 🔒 4️⃣ Vô hiệu hóa tài khoản
# =========================================================
@user_router.get("/deactivate/{user_id}")
def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    """Vô hiệu hóa tài khoản (inactive thay vì xóa)"""
    try:
        user_service.deactivate_user(user_id, db)
    except Exception as e:
        print(f"❌ Lỗi vô hiệu hóa user: {e}")
    return RedirectResponse("/admin/Account/manage-users", status_code=303)

# =========================================================
# 🔓 5️⃣ Khôi phục tài khoản
# =========================================================
@user_router.get("/restore/{user_id}")
def restore_user(user_id: str, db: Session = Depends(get_db)):
    """Khôi phục tài khoản đã bị vô hiệu hóa"""
    try:
        user_service.restore_user(user_id, db)
    except Exception as e:
        print(f"❌ Lỗi khôi phục user: {e}")
    return RedirectResponse("/admin/Account/manage-users", status_code=303)
