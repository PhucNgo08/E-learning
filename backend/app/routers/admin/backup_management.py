from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import traceback

# ==============================
# 🧩 Import database & services
# ==============================
from app.database.connection import get_db
from app.services.admin.backup_management_service import (
    get_all_backups,
    create_backup,
    delete_backup,
    create_backup_schedule,
    cleanup_old_backups
)

# Template config
from app.config.template_config import get_template_by_path


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
    try:
        tpl = get_template_by_path(request.url.path)
        backups = get_all_backups(db)
        return tpl.TemplateResponse(
            "backups/manage_backups.html",
            {"request": request, "backups": backups}
        )
    except Exception:
        traceback.print_exc()
        raise HTTPException(500, "Lỗi khi truy vấn danh sách backup.")


# =========================================================
# ➕ 2️⃣ Form tạo backup
# =========================================================
@backup_router.get("/create", response_class=HTMLResponse)
def create_backup_form(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "backups/create_backup.html",
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
    try:
        create_backup(database_name, backup_type, db)
        return RedirectResponse("/admin/backups/manage", status_code=303)
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi tạo backup: {str(e)}")


# =========================================================
# 📥 4️⃣ Download backup file
# =========================================================
@backup_router.get("/download/{backup_id}")
def download_backup(backup_id: str, db: Session = Depends(get_db)):
    from app.models.backup_history import BackupHistory

    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise HTTPException(404, "Không tìm thấy bản sao lưu.")

    file_path = Path(backup.file_path)
    if not file_path.exists():
        raise HTTPException(404, "File không tồn tại trên máy chủ.")

    return FileResponse(path=file_path, filename=file_path.name, media_type="application/octet-stream")


# =========================================================
# ❌ 5️⃣ Form xác nhận xóa
# =========================================================
@backup_router.get("/delete/{backup_id}", response_class=HTMLResponse)
def confirm_delete(request: Request, backup_id: str, db: Session = Depends(get_db)):
    from app.models.backup_history import BackupHistory

    backup = db.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
    if not backup:
        raise HTTPException(404, "Không tìm thấy bản sao lưu.")

    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "backups/delete_backup.html",
        {"request": request, "backup": backup}
    )


# =========================================================
# 🗑️ 6️⃣ Xử lý xóa backup
# =========================================================
@backup_router.post("/delete/{backup_id}")
def handle_delete_backup(backup_id: str, db: Session = Depends(get_db)):
    try:
        delete_backup(backup_id, db)
        return RedirectResponse("/admin/backups/manage", status_code=303)
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi xóa backup: {str(e)}")


# =========================================================
# 📅 7️⃣ Form tạo lịch backup (gọi stored procedure)
# =========================================================
@backup_router.get("/schedule/create", response_class=HTMLResponse)
def schedule_form(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "backups/create_schedule.html",
        {"request": request}
    )


# =========================================================
# 🆕 8️⃣ Xử lý tạo lịch backup (CALL sp_create_backup_schedule)
# =========================================================
@backup_router.post("/schedule/create")
def handle_create_schedule(
    schedule_name: str = Form(...),
    backup_type: str = Form("full"),
    frequency: str = Form("daily"),
    retention_days: int = Form(30),
    db: Session = Depends(get_db)
):
    try:
        create_backup_schedule(schedule_name, backup_type, frequency, retention_days, db)
        return RedirectResponse("/admin/backups/manage", status_code=303)
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi tạo lịch backup: {str(e)}")


# =========================================================
# 🧹 9️⃣ Cleanup backup cũ (CALL sp_cleanup_old_backups)
# =========================================================
@backup_router.post("/cleanup")
def handle_cleanup(db: Session = Depends(get_db)):
    try:
        result = cleanup_old_backups(db)
        print("Cleanup result:", result)
        return RedirectResponse("/admin/backups/manage", status_code=303)
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi dọn backup cũ: {str(e)}")
