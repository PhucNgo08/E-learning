"""
==========================================================
📂 ROUTER: Admin - File Storage Management
Quản lý file upload, CDN cache và tối ưu dung lượng
==========================================================
"""

from datetime import datetime
from urllib.parse import quote

from fastapi import (
    APIRouter, Request, Depends, UploadFile, File, Form, HTTPException, Query, status
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.config.template_config import get_template_by_path

from app.services.admin.file_storage_service import (
    upload_file_service,
    delete_file_service,
    refresh_cdn_cache_service,
    get_storage_stats_service
)
from app.models.file_storage import FileStorage
from app.models.cdn_cache import CDNCache


router = APIRouter(
    prefix="/admin/file-storage",
    tags=["Admin - File Storage"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "file_storage",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/list", response_class=HTMLResponse)
def list_files(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    del current_user

    files = db.query(FileStorage).order_by(FileStorage.created_at.desc()).all()
    cdn_data = {c.file_id: c for c in db.query(CDNCache).all()}

    return render_template(
        request,
        "file_storage/list.html",
        {
            "files": files,
            "cdn_data": cdn_data,
            "total": len(files),
            "success": success,
            "error": error,
            "page_title": "📦 Quản lý File lưu trữ",
        }
    )


@router.get("/upload", response_class=HTMLResponse)
def upload_form(
    request: Request,
    current_user=Depends(get_current_admin)
):
    del current_user

    return render_template(
        request,
        "file_storage/upload.html",
        {
            "page_title": "📤 Upload File mới",
            "error": None,
            "form_data": {
                "storage_provider": "local",
                "is_public": 1,
            },
        },
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_submit(
    request: Request,
    file: UploadFile = File(...),
    storage_provider: str = Form("local"),
    is_public: int = Form(1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    form_data = {
        "storage_provider": storage_provider,
        "is_public": is_public,
    }

    try:
        upload_file_service(
            file=file,
            db=db,
            uploaded_by=current_user.id,
            storage_provider=storage_provider,
            is_public=is_public
        )

        message = quote("Upload file thành công.")
        return RedirectResponse(
            url=f"/admin/file-storage/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except ValueError as e:
        return render_template(
            request,
            "file_storage/upload.html",
            {
                "page_title": "📤 Upload File mới",
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "file_storage/upload.html",
            {
                "page_title": "📤 Upload File mới",
                "error": f"Lỗi khi upload file: {str(e)}",
                "form_data": form_data,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/cdn/cache")
def refresh_cache(
    file_id: str = Form(...),
    cdn_provider: str = Form("cloudflare"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    del current_user

    try:
        updated = refresh_cdn_cache_service(db, file_id, cdn_provider)
        if not updated:
            raise ValueError("Không tìm thấy file để cache.")

        message = quote("Làm mới CDN cache thành công.")
        return RedirectResponse(
            url=f"/admin/file-storage/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/file-storage/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        message = quote(f"Lỗi khi làm mới CDN cache: {str(e)}")
        return RedirectResponse(
            url=f"/admin/file-storage/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/delete/{file_id}", response_class=HTMLResponse)
def confirm_delete(
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    del current_user

    file_data = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file_data:
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")

    return render_template(
        request,
        "file_storage/delete.html",
        {
            "file": file_data,
            "page_title": "🗑️ Xóa File",
        },
    )


@router.post("/delete/{file_id}")
def delete_file_action(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    del current_user

    try:
        deleted = delete_file_service(db, file_id)
        if not deleted:
            raise ValueError("File không tồn tại.")

        message = quote("Xóa file thành công.")
        return RedirectResponse(
            url=f"/admin/file-storage/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/file-storage/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        message = quote(f"Lỗi khi xóa file: {str(e)}")
        return RedirectResponse(
            url=f"/admin/file-storage/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )


@router.get("/stats", response_class=HTMLResponse)
def storage_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    del current_user

    stats = get_storage_stats_service(db)
    return render_template(
        request,
        "file_storage/stats.html",
        {
            "stats": stats,
            "page_title": "📊 Thống kê Lưu trữ File",
        },
    )