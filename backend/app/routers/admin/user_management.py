from datetime import datetime
import csv
import io
from typing import Optional
from urllib.parse import quote
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.services import user_service
from app.services.admin.user_statistics_service import get_user_statistics

logger = logging.getLogger(__name__)

user_router = APIRouter(
    prefix="/admin/Account",
    tags=["Admin - User Management"],
    dependencies=[Depends(get_current_admin)],
)


# ============================================================
# HELPERS
# ============================================================
def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def get_friendly_error(exc: Exception) -> tuple[str, str]:
    raw = str(getattr(exc, "orig", exc)).lower()

    if isinstance(exc, HTTPException):
        if exc.status_code == 404:
            return ("Không tìm thấy dữ liệu", exc.detail or "Người dùng bạn cần thao tác không tồn tại.")
        if exc.status_code == 400:
            return ("Dữ liệu chưa hợp lệ", exc.detail or "Vui lòng kiểm tra lại các thông tin đã nhập.")
        if exc.status_code == 403:
            return ("Bạn không có quyền thực hiện", exc.detail or "Thao tác này không được phép.")

    if isinstance(exc, IntegrityError):
        if "username" in raw:
            return ("Tên đăng nhập đã tồn tại", "Vui lòng chọn tên đăng nhập khác.")
        if "email" in raw:
            return ("Email đã được sử dụng", "Vui lòng dùng email khác hoặc kiểm tra lại tài khoản đã tồn tại.")
        if "mssv" in raw:
            return ("MSSV đã tồn tại", "Mã số sinh viên này đã được gán cho tài khoản khác.")
        if "foreign key" in raw:
            return ("Dữ liệu liên kết không hợp lệ", "Năm học, ngành học hoặc role bạn chọn không còn tồn tại.")
        return (
            "Không thể lưu dữ liệu",
            "Dữ liệu có thể đang bị trùng hoặc chưa đúng định dạng. Vui lòng kiểm tra lại.",
        )

    if isinstance(exc, ValueError):
        message = str(exc).strip() or "Vui lòng kiểm tra lại dữ liệu."
        lowered = message.lower()

        if "không tìm thấy người dùng" in lowered:
            return ("Không tìm thấy người dùng", message)
        if "admin" in lowered and ("xóa" in lowered or "vô hiệu hóa" in lowered):
            return ("Không thể thao tác với tài khoản admin", message)
        if "đã bị vô hiệu hóa" in lowered:
            return ("Tài khoản đã bị vô hiệu hóa", message)
        if "đang hoạt động" in lowered:
            return ("Tài khoản đang hoạt động", message)
        if "dữ liệu liên kết" in lowered:
            return ("Không thể xóa vĩnh viễn", message)

        return ("Dữ liệu chưa hợp lệ", message)

    if isinstance(exc, SQLAlchemyError):
        logger.exception("Database error: %s", exc)
        return ("Lỗi cơ sở dữ liệu", "Hệ thống chưa thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.")

    logger.exception("Unexpected error: %s", exc)
    return ("Đã có lỗi xảy ra", "Có sự cố ngoài mong muốn. Vui lòng thử lại sau hoặc liên hệ quản trị viên.")


def _role_value(user) -> str:
    return str(getattr(user, "resolved_role", None) or getattr(user, "role", None) or "student")


# ============================================================
# 1. LIST USERS
# ============================================================
@user_router.get("/manage-users", response_class=HTMLResponse)
def manage_users(request: Request, db: Session = Depends(get_db)):
    users = user_service.get_all_users(db)
    return render_template(
        request,
        "Account/list_users.html",
        {
            "users": users,
            "page_title": "👥 Danh sách người dùng",
            "success_message": request.query_params.get("success"),
            "warning_message": request.query_params.get("warning"),
            "error_message": request.query_params.get("error"),
        },
    )


# ============================================================
# 2. ADD USER
# ============================================================
@user_router.get("/add-user", response_class=HTMLResponse)
def add_user_form(request: Request, db: Session = Depends(get_db)):
    academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
    majors = db.query(Major).order_by(Major.major_name).all()

    return render_template(
        request,
        "Account/add_user.html",
        {
            "academic_years": academic_years,
            "majors": majors,
            "form_data": {},
        },
    )


@user_router.post("/add-user")
def add_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    academic_year_id: Optional[str] = Form(None),
    major_id: Optional[str] = Form(None),
    mssv: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    form_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "role": role,
        "academic_year_id": academic_year_id or "",
        "major_id": major_id or "",
        "mssv": mssv or "",
    }

    try:
        user_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=role,
            db=db,
            academic_year_id=academic_year_id,
            major_id=major_id,
            mssv=mssv,
        )
        return RedirectResponse(
            "/admin/Account/manage-users?success=" + quote("Thêm người dùng thành công."),
            status_code=303,
        )

    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.warning("Add user failed: %s", exc)

        academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
        majors = db.query(Major).order_by(Major.major_name).all()

        return render_template(
            request,
            "Account/add_user.html",
            {
                "error_title": error_title,
                "error_message": error_message,
                "academic_years": academic_years,
                "majors": majors,
                "form_data": form_data,
            },
            status_code=400,
        )


# ============================================================
# 3. EDIT USER
# ============================================================
@user_router.get("/edit-user/{user_id}", response_class=HTMLResponse)
def edit_user_form(request: Request, user_id: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_id(user_id, db)
    if not user:
        return RedirectResponse(
            "/admin/Account/manage-users?error=" + quote("Không tìm thấy người dùng cần chỉnh sửa."),
            status_code=303,
        )

    academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
    majors = db.query(Major).order_by(Major.major_name).all()

    return render_template(
        request,
        "Account/edit_user.html",
        {
            "user": user,
            "academic_years": academic_years,
            "majors": majors,
            "form_data": {
                "username": user.username,
                "email": user.email,
                "full_name": getattr(user, "full_name", None) or getattr(user, "resolved_full_name", None) or "",
                "role": _role_value(user),
                "academic_year_id": str(getattr(user, "academic_year_id", "") or ""),
                "major_id": str(getattr(user, "major_id", "") or ""),
                "mssv": getattr(user, "mssv", "") or "",
            },
        },
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
    academic_year_id: Optional[str] = Form(None),
    major_id: Optional[str] = Form(None),
    mssv: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    form_data = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "role": role,
        "academic_year_id": academic_year_id or "",
        "major_id": major_id or "",
        "mssv": mssv or "",
    }

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
            major_id=major_id,
            mssv=mssv,
        )
        return RedirectResponse(
            "/admin/Account/manage-users?success=" + quote("Cập nhật người dùng thành công."),
            status_code=303,
        )

    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.warning("Edit user failed [%s]: %s", user_id, exc)

        user = user_service.get_user_by_id(user_id, db)
        academic_years = db.query(AcademicYear).order_by(AcademicYear.start_year).all()
        majors = db.query(Major).order_by(Major.major_name).all()

        return render_template(
            request,
            "Account/edit_user.html",
            {
                "user": user,
                "error_title": error_title,
                "error_message": error_message,
                "academic_years": academic_years,
                "majors": majors,
                "form_data": form_data,
            },
            status_code=400,
        )


# ============================================================
# 4. DELETE USER
# ============================================================
@user_router.post("/delete/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    try:
        result = user_service.delete_user_safely(user_id, db)

        if result["action"] == "deleted":
            return RedirectResponse(
                "/admin/Account/manage-users?success=" + quote(result["message"]),
                status_code=303,
            )

        if result["action"] == "deactivated":
            return RedirectResponse(
                "/admin/Account/manage-users?warning=" + quote(result["message"]),
                status_code=303,
            )

        return RedirectResponse(
            "/admin/Account/manage-users?error=" + quote("Không thể xử lý yêu cầu xóa tài khoản."),
            status_code=303,
        )

    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.warning("%s - %s", error_title, exc)
        return RedirectResponse(
            "/admin/Account/manage-users?error=" + quote(error_message),
            status_code=303,
        )


# ============================================================
# 5. DEACTIVATE USER
# ============================================================
@user_router.post("/deactivate/{user_id}")
def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    try:
        user_service.deactivate_user(user_id, db)
        return RedirectResponse(
            "/admin/Account/manage-users?success=" + quote("Đã vô hiệu hóa tài khoản."),
            status_code=303,
        )
    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.warning("%s - %s", error_title, exc)
        return RedirectResponse(
            "/admin/Account/manage-users?error=" + quote(error_message),
            status_code=303,
        )


# ============================================================
# 6. RESTORE USER
# ============================================================
@user_router.post("/restore/{user_id}")
def restore_user(user_id: str, db: Session = Depends(get_db)):
    try:
        user_service.restore_user(user_id, db)
        return RedirectResponse(
            "/admin/Account/manage-users?success=" + quote("Đã khôi phục tài khoản."),
            status_code=303,
        )
    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.warning("%s - %s", error_title, exc)
        return RedirectResponse(
            "/admin/Account/manage-users?error=" + quote(error_message),
            status_code=303,
        )


# ============================================================
# 7. USER STATISTICS
# ============================================================
@user_router.get("/statistics", response_class=HTMLResponse)
def user_statistics(request: Request, db: Session = Depends(get_db)):
    try:
        stats = get_user_statistics(db)
        return render_template(
            request,
            "Account/statistics.html",
            {
                "stats": stats,
                "page_title": "📈 Thống kê người dùng",
            },
        )
    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.exception("Lỗi khi lấy thống kê người dùng: %s", exc)
        return render_template(
            request,
            "Account/statistics.html",
            {
                "stats": {},
                "page_title": "📈 Thống kê người dùng",
                "error_title": error_title,
                "error_message": error_message,
            },
            status_code=500,
        )


# ============================================================
# 5. EXPORT USERS
# ============================================================
@user_router.get("/export-users")
def export_users(db: Session = Depends(get_db)):
    """
    Xuất danh sách người dùng dạng CSV để tải về.
    Giữ route cũ /admin/Account/export-users đang được nút trên giao diện gọi.
    """
    users = user_service.get_all_users(db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Tên đăng nhập",
        "Email",
        "Họ và tên",
        "Vai trò",
        "Trạng thái",
        "Ngày tạo",
    ])

    for user in users:
        profile = getattr(user, "profile", None)
        full_name = getattr(profile, "full_name", "") if profile else getattr(user, "full_name", "")
        created_at = getattr(user, "created_at", "")
        if hasattr(created_at, "strftime"):
            created_at = created_at.strftime("%d/%m/%Y %H:%M")

        writer.writerow([
            getattr(user, "username", ""),
            getattr(user, "email", ""),
            full_name or "",
            _role_value(user),
            getattr(user, "status", ""),
            created_at or "",
        ])

    output.seek(0)
    filename = f"danh_sach_nguoi_dung_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "text/csv; charset=utf-8-sig",
    }
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv",
        headers=headers,
    )


# ============================================================
# 6. USER STATISTICS
# ============================================================
@user_router.get("/statistics", response_class=HTMLResponse)
def user_statistics(request: Request, db: Session = Depends(get_db)):
    try:
        stats = get_user_statistics(db)
        return render_template(
            request,
            "Account/statistics.html",
            {
                "stats": stats,
                "page_title": "📈 Thống kê người dùng",
            },
        )
    except Exception as exc:
        error_title, error_message = get_friendly_error(exc)
        logger.exception("Lỗi khi lấy thống kê người dùng: %s", exc)
        return render_template(
            request,
            "Account/statistics.html",
            {
                "stats": {},
                "page_title": "📈 Thống kê người dùng",
                "error_title": error_title,
                "error_message": error_message,
            },
            status_code=500,
        )
