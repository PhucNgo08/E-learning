from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.services.admin.backup_management_service import (
    cleanup_old_backups,
    create_backup,
    create_backup_schedule,
    delete_backup,
    delete_backup_schedule,
    get_all_backups,
    get_all_backup_schedules,
    get_backup_by_id,
    get_backup_schedule_by_id,
)

backup_router = APIRouter(
    prefix="/admin/backups",
    tags=["Admin - Backup Management"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


# =========================================================
# 1) Danh sách backup
# =========================================================
@backup_router.get("/manage", response_class=HTMLResponse)
def manage_backups(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    backups = get_all_backups(db)
    return render_template(
        request,
        "backups/manage_backups.html",
        {
            "backups": backups,
            "success": success,
            "error": error,
        }
    )


# =========================================================
# 2) Form tạo backup
# =========================================================
@backup_router.get("/create", response_class=HTMLResponse)
def create_backup_form(request: Request):
    return render_template(
        request,
        "backups/create_backup.html",
        {
            "form_data": {
                "database_name": "e_learning",
                "backup_type": "full",
                "note": "",
            }
        }
    )


# =========================================================
# 3) Xử lý tạo backup
# =========================================================
@backup_router.post("/create", response_class=HTMLResponse)
def handle_create_backup(
    request: Request,
    database_name: str = Form("e_learning"),
    backup_type: str = Form("full"),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    form_data = {
        "database_name": database_name,
        "backup_type": backup_type,
        "note": note,
    }

    try:
        create_backup(
            database_name=database_name,
            backup_type=backup_type,
            note=note,
            db=db,
        )
        message = quote("Tạo backup thành công.")
        return RedirectResponse(
            url=f"/admin/backups/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return render_template(
            request,
            "backups/create_backup.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "backups/create_backup.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =========================================================
# 4) Download backup file
# =========================================================
@backup_router.get("/download/{backup_id}")
def download_backup(backup_id: str, db: Session = Depends(get_db)):
    backup = get_backup_by_id(backup_id, db)
    if not backup:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao lưu.")

    file_path = Path(backup.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại trên máy chủ.")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


# =========================================================
# 5) Form xác nhận xóa
# =========================================================
@backup_router.get("/delete/{backup_id}", response_class=HTMLResponse)
def confirm_delete(request: Request, backup_id: str, db: Session = Depends(get_db)):
    backup = get_backup_by_id(backup_id, db)
    if not backup:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản sao lưu.")

    return render_template(
        request,
        "backups/delete_backup.html",
        {"backup": backup}
    )


# =========================================================
# 6) Xử lý xóa backup
# =========================================================
@backup_router.post("/delete/{backup_id}")
def handle_delete_backup(backup_id: str, db: Session = Depends(get_db)):
    try:
        delete_backup(backup_id, db)
        message = quote("Xóa backup thành công.")
        return RedirectResponse(
            url=f"/admin/backups/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/backups/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/backups/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# =========================================================
# 7) Danh sách lịch backup
# =========================================================
@backup_router.get("/schedule/manage", response_class=HTMLResponse)
def manage_schedules(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    schedules = get_all_backup_schedules(db)
    return render_template(
        request,
        "backups/manage_schedules.html",
        {
            "schedules": schedules,
            "success": success,
            "error": error,
        }
    )


# =========================================================
# 8) Form tạo lịch backup
# =========================================================
@backup_router.get("/schedule/create", response_class=HTMLResponse)
def schedule_form(request: Request):
    return render_template(
        request,
        "backups/create_schedule.html",
        {
            "form_data": {
                "schedule_name": "",
                "backup_type": "full",
                "frequency": "daily",
                "retention_days": 30,
            }
        }
    )


# =========================================================
# 9) Xử lý tạo lịch backup
# =========================================================
@backup_router.post("/schedule/create", response_class=HTMLResponse)
def handle_create_schedule(
    request: Request,
    schedule_name: str = Form(...),
    backup_type: str = Form("full"),
    frequency: str = Form("daily"),
    retention_days: int = Form(30),
    db: Session = Depends(get_db),
):
    form_data = {
        "schedule_name": schedule_name,
        "backup_type": backup_type,
        "frequency": frequency,
        "retention_days": retention_days,
    }

    try:
        create_backup_schedule(
            schedule_name=schedule_name,
            schedule_type=backup_type,
            freq=frequency,
            retention_days=retention_days,
            db=db,
        )
        message = quote("Tạo lịch backup thành công.")
        return RedirectResponse(
            url=f"/admin/backups/schedule/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return render_template(
            request,
            "backups/create_schedule.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "backups/create_schedule.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =========================================================
# 10) Xóa lịch backup
# =========================================================
@backup_router.post("/schedule/delete/{schedule_id}")
def handle_delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    try:
        schedule = get_backup_schedule_by_id(schedule_id, db)
        if not schedule:
            raise ValueError("Không tìm thấy lịch backup.")

        delete_backup_schedule(schedule_id, db)
        message = quote("Xóa lịch backup thành công.")
        return RedirectResponse(
            url=f"/admin/backups/schedule/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/backups/schedule/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/backups/schedule/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


# =========================================================
# 11) Cleanup backup cũ
# =========================================================
@backup_router.post("/cleanup")
def handle_cleanup(db: Session = Depends(get_db)):
    try:
        result = cleanup_old_backups(db)
        message = quote(result.get("message", "Dọn backup cũ thành công."))
        return RedirectResponse(
            url=f"/admin/backups/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/backups/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )