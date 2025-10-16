from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services import system_setting_service
from pathlib import Path
import traceback

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/settings"
)
# ============================================================
# ⚙️ Router cấu hình hệ thống

router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin - System Settings"]
)


@router.get("/manage", response_class=HTMLResponse)
def manage_settings(request: Request, db: Session = Depends(get_db)):
    try:
        settings = system_setting_service.get_all_settings(db)
        return templates.TemplateResponse("manage.html", {
            "request": request,
            "settings": settings
        })
    except Exception:
        print("\n❌ LỖI TẢI TRANG CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)


@router.post("/update")
def update_setting(
    key: str = Form(...),
    value: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        system_setting_service.update_setting(db, key, value, description)
        return RedirectResponse(url="/admin/settings/manage", status_code=303)
    except Exception:
        print("\n❌ LỖI CẬP NHẬT CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)


# =========================================================
# ➕ 3️⃣ Tạo mới cấu hình
# =========================================================
@router.post("/create")
def create_setting(
    key: str = Form(...),
    value: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Tạo mới cấu hình hệ thống
    """
    try:
        system_setting_service.update_setting(db, key, value, description)
        return RedirectResponse(url="/admin/settings/manage", status_code=303)
    except Exception:
        print("\n❌ LỖI TẠO CẤU HÌNH:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
# ============================================================
# ✏️ 4️⃣ Chỉnh sửa cấu hình (tuỳ chọn)
# ============================================================
# (Có thể không cần, vì ta có thể chỉnh trực tiếp trên trang quản lý)