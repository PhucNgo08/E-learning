"""
==========================================================
📂 ROUTER: Admin - File Storage Management
Quản lý file upload, CDN cache và tối ưu dung lượng
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.config.template_config import get_template_by_path

# ✅ Import services
from app.services.admin.file_storage_service import (
    upload_file_service,
    delete_file_service,
    refresh_cdn_cache_service,
    get_storage_stats_service
)
from app.models.file_storage import FileStorage
from app.models.cdn_cache import CDNCache


# ==========================================================
# ⚙️ Router
# ==========================================================
router = APIRouter(
    prefix="/admin/file-storage",
    tags=["Admin - File Storage"]
)


# ==========================================================
# 📄 1️⃣ Danh sách File
# ==========================================================
@router.get("/list", response_class=HTMLResponse)
def list_files(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Hiển thị danh sách file đã upload"""
    tpl = get_template_by_path(request.url.path)
    files = db.query(FileStorage).order_by(FileStorage.created_at.desc()).all()
    cdn_data = {c.file_id: c for c in db.query(CDNCache).all()}
    total = len(files)

    return tpl.TemplateResponse(
        "file_storage/list.html",  # ✅ bỏ chữ "admin/"
        {
            "request": request,
            "files": files,
            "cdn_data": cdn_data,
            "total": total,
            "page_title": "📦 Quản lý File lưu trữ",
            "active_page": "file_storage",
        }
    )


# ==========================================================
# ➕ 2️⃣ Upload File
# ==========================================================
@router.get("/upload", response_class=HTMLResponse)
def upload_form(request: Request, current_user=Depends(get_current_admin)):
    """Trang upload file"""
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "file_storage/upload.html",  # ✅ bỏ "admin/"
        {
            "request": request,
            "page_title": "📤 Upload File mới",
            "active_page": "file_storage",
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
    """Xử lý upload file"""
    try:
        upload_file_service(
            file=file,
            db=db,
            uploaded_by=current_user.id,
            storage_provider=storage_provider,
            is_public=is_public
        )
        return RedirectResponse(url="/admin/file-storage/list", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi khi upload file: {e}")


# ==========================================================
# ✏️ 3️⃣ Làm mới CDN Cache
# ==========================================================
@router.post("/cdn/cache")
def refresh_cache(
    file_id: str = Form(...),
    cdn_provider: str = Form("cloudflare"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Cập nhật CDN cache"""
    updated = refresh_cdn_cache_service(db, file_id, cdn_provider)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy file để cache.")
    return RedirectResponse(url="/admin/file-storage/list", status_code=303)


# ==========================================================
# 🗑️ 4️⃣ Xóa File
# ==========================================================
@router.get("/delete/{file_id}", response_class=HTMLResponse)
def confirm_delete(
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Hiển thị trang xác nhận xóa file"""
    tpl = get_template_by_path(request.url.path)
    file_data = db.query(FileStorage).filter(FileStorage.id == file_id).first()
    if not file_data:
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")
    return tpl.TemplateResponse(
        "file_storage/delete.html",  # ✅ bỏ "admin/"
        {
            "request": request,
            "file": file_data,
            "page_title": "🗑️ Xóa File",
            "active_page": "file_storage",
        },
    )


@router.post("/delete/{file_id}")
def delete_file_action(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Xóa file khỏi DB và thư mục"""
    deleted = delete_file_service(db, file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File không tồn tại.")
    return RedirectResponse(url="/admin/file-storage/list", status_code=303)


# ==========================================================
# 📊 5️⃣ Thống kê lưu trữ
# ==========================================================
@router.get("/stats", response_class=HTMLResponse)
def storage_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Hiển thị thống kê file lưu trữ"""
    tpl = get_template_by_path(request.url.path)
    stats = get_storage_stats_service(db)
    return tpl.TemplateResponse(
        "file_storage/stats.html",  # ✅ bỏ "admin/"
        {
            "request": request,
            "stats": stats,
            "page_title": "📊 Thống kê Lưu trữ File",
            "active_page": "file_storage",
        },
    )
