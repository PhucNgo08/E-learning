from fastapi import (
    APIRouter, Request, Form, Depends, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.backup_management_service import (
    get_all_backups,
    create_backup,
    delete_backup
)
from pathlib import Path

# ==============================
# 🧭 Cấu hình template
# ==============================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/backups"
)

# ==============================
# 🚀 Khởi tạo router
# ==============================
backup_router = APIRouter(
    prefix="/admin/backups",
    tags=["Admin - Backup Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách backup
# =========================================================
@backup_router.get("/manage", response_class=HTMLResponse)
def manage_backups(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách tất cả các bản sao lưu.
    """
    try:
        backups = get_all_backups(db)
        return templates.TemplateResponse(
            "manage_backups.html",
            {"request": request, "backups": backups}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy vấn backup: {str(e)}")


# =========================================================
# ➕ 2️⃣ Form tạo backup
# =========================================================
@backup_router.get("/create", response_class=HTMLResponse)
def create_backup_form(request: Request):
    """
    Hiển thị form tạo bản sao lưu mới.
    """
    return templates.TemplateResponse(
        "create_backup.html",
        {"request": request}
    )

# =========================================================
# 💾 3️⃣ Xử lý tạo backup
# =========================================================
@backup_router.post("/create")
def handle_create_backup(
    database_name: str = Form("e_learning"),
    backup_type: str = Form("full"),
    db: Session = Depends(get_db)
):
    """
    Xử lý tạo backup (ghi vào DB và file vật lý).
    """
    try:
        create_backup(database_name, backup_type, db)
        return RedirectResponse(
            url="/admin/backups/manage",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo backup: {str(e)}")

# =========================================================
# 📥 4️⃣ Tải file backup
# =========================================================
@backup_router.get("/download/{backup_id}")
def download_backup(backup_id: str, db: Session = Depends(get_db)):
    """
    Cho phép tải file backup nếu tồn tại.
    """
    from app.models.backup_history import BackupHistory
    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao lưu.")

    file_path = Path(backup.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File sao lưu không tồn tại trên máy chủ.")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )

# =========================================================
# ❌ 5️⃣ Xác nhận xóa backup
# =========================================================
@backup_router.get("/delete/{backup_id}", response_class=HTMLResponse)
def confirm_delete(
    request: Request,
    backup_id: str,
    db: Session = Depends(get_db)
):
    """
    Hiển thị trang xác nhận xóa bản sao lưu.
    """
    from app.models.backup_history import BackupHistory
    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()

    if not backup:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao lưu.")

    return templates.TemplateResponse(
        "delete_backup.html",
        {"request": request, "backup": backup}
    )

# =========================================================
# 🗑️ 6️⃣ Xử lý xóa backup
# =========================================================
@backup_router.post("/delete/{backup_id}")
def handle_delete_backup(backup_id: str, db: Session = Depends(get_db)):
    """
    Xóa bản sao lưu khỏi cơ sở dữ liệu và xóa file vật lý nếu có.
    """
    try:
        delete_backup(backup_id, db)
        return RedirectResponse(
            url="/admin/backups/manage",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa backup: {str(e)}")
# ============================================================
