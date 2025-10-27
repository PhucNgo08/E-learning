from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin import system_setting_service
import traceback

# ✅ Import hệ thống template config dùng chung
from app.config.template_config import get_template_by_path

# ============================================================
# ⚙️ Router: Cấu hình hệ thống (System Settings)
# ============================================================
router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin - System Settings"]
)

# ============================================================
# 📋 1️⃣ Quản lý cấu hình
# ============================================================
@router.get("/manage", response_class=HTMLResponse)
def manage_settings(request: Request, db: Session = Depends(get_db)):
    """
    Trang hiển thị danh sách tất cả các cài đặt hệ thống.
    """
    tpl = get_template_by_path(request.url.path)
    try:
        settings = system_setting_service.get_all_settings(db)
        return tpl.TemplateResponse(
            "settings/manage.html",
            {
                "request": request,
                "settings": settings,
                "page_title": "⚙️ Cấu hình hệ thống"
            },
        )
    except Exception:
        print("\n❌ LỖI TẢI TRANG CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# ============================================================
# 💾 2️⃣ Cập nhật cấu hình
# ============================================================
@router.post("/update")
def update_setting(
    key: str = Form(...),
    value: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Cập nhật giá trị cấu hình hệ thống.
    """
    try:
        system_setting_service.update_setting(db, key, value, description)
        return RedirectResponse(url="/admin/settings/manage", status_code=303)
    except Exception:
        print("\n❌ LỖI CẬP NHẬT CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# ============================================================
# ➕ 3️⃣ Tạo mới cấu hình
# ============================================================
@router.post("/create")
def create_setting(
    key: str = Form(...),
    value: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Tạo mới cấu hình hệ thống.
    """
    try:
        # Nếu key đã tồn tại → cập nhật, ngược lại → tạo mới
        system_setting_service.update_setting(db, key, value, description)
        return RedirectResponse(url="/admin/settings/manage", status_code=303)
    except Exception:
        print("\n❌ LỖI TẠO CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# ============================================================
# ✏️ 4️⃣ Xóa cấu hình
# ============================================================
@router.get("/delete/{key}", response_class=HTMLResponse)
def delete_setting(key: str, db: Session = Depends(get_db)):
    """
    Xóa cấu hình hệ thống theo key.
    """
    try:
        system_setting_service.delete_setting(db, key)
        return RedirectResponse(url="/admin/settings/manage", status_code=303)
    except Exception:
        print("\n❌ LỖI XÓA CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# ============================================================
# ✅ 5️⃣ Kiểm tra key cấu hình có tồn tại không (AJAX)
# ============================================================
@router.get("/validate", response_class=HTMLResponse)
def settings_validate(request: Request, key: str, db: Session = Depends(get_db)):
    """
    API kiểm tra nhanh key cấu hình đã tồn tại hay chưa.
    Trả về template nhỏ dùng cho AJAX.
    """
    tpl = get_template_by_path(request.url.path)
    try:
        setting = system_setting_service.get_setting_by_key(db, key)
        setting_exists = setting is not None
        return tpl.TemplateResponse(
            "settings/settings_validate.html",
            {
                "request": request,
                "key": key,
                "setting_exists": setting_exists,
            },
        )
    except Exception:
        print("\n❌ LỖI KIỂM TRA KEY CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
