from __future__ import annotations

import html
import traceback
from datetime import datetime
from pathlib import Path

import app.models  # noqa: F401
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config.paths import UPLOADS_BASE
from app.core.config import get_settings

settings = get_settings()

if settings.SESSION_SECRET_KEY == "dev-insecure-change-me":
    print("⚠️ SESSION_SECRET_KEY chưa được cấu hình. Đang dùng khóa dev tạm thời.")


# =====================================================
# FASTAPI APP
# =====================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="🌐 Hệ thống quản lý học tập trực tuyến - FastAPI",
)


# =====================================================
# SESSION MIDDLEWARE
# =====================================================
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.session_max_age_seconds,
    same_site=settings.SESSION_SAME_SITE,
    https_only=settings.session_https_only,
)

from app.middleware.session_expire_checker import SessionExpireMiddleware  # noqa: E402

app.add_middleware(SessionExpireMiddleware)


# =====================================================
# CORS
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# STATIC & TEMPLATE SETUP
# =====================================================
ROOT = Path(__file__).resolve().parent.parent.parent

FRONTEND_DIR = ROOT / "frontend" / "react-app"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATE_DIR = FRONTEND_DIR / "layouts" / "templates"
STYLE_DIR = FRONTEND_DIR / "layouts" / "styles"


def _mount_static_if_exists(url_path: str, directory: Path, name: str) -> None:
    if directory.exists() and directory.is_dir():
        app.mount(url_path, StaticFiles(directory=str(directory)), name=name)
    else:
        print(f"⚠️ Static directory missing: {directory}")


_mount_static_if_exists("/static", STATIC_DIR, "static")
_mount_static_if_exists("/styles", STYLE_DIR, "styles")
_mount_static_if_exists(
    "/frontend/react-app/layouts/styles",
    STYLE_DIR,
    "styles_legacy",
)

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.templates = templates
app.admin_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "admin"))
app.teacher_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "teacher"))
app.student_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "student"))

for env in [
    templates.env,
    app.admin_templates.env,
    app.teacher_templates.env,
    app.student_templates.env,
]:
    env.globals.update(
        now=datetime.now,
        app_env=settings.APP_ENV,
    )


# =====================================================
# UPLOADS DIR
# =====================================================
if UPLOADS_BASE.exists() and UPLOADS_BASE.is_dir():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_BASE)), name="uploads")
else:
    print("⚠️ UPLOADS folder missing:", UPLOADS_BASE)

DEFAULT_AVATAR_PATH = UPLOADS_BASE / "avatars" / "default-avatar.png"


@app.get("/uploads/avatars/{filename}")
async def serve_avatar(filename: str):
    avatar_path = UPLOADS_BASE / "avatars" / filename
    if avatar_path.exists():
        return FileResponse(avatar_path)

    if DEFAULT_AVATAR_PATH.exists():
        return FileResponse(DEFAULT_AVATAR_PATH)

    return HTMLResponse("Avatar not found", status_code=404)


# =====================================================
# ERROR HELPERS
# =====================================================
def wants_json(request: Request) -> bool:
    accept = (request.headers.get("accept") or "").lower()
    content_type = (request.headers.get("content-type") or "").lower()
    requested_with = (request.headers.get("x-requested-with") or "").lower()

    return (
        request.url.path.startswith("/api")
        or "application/json" in accept
        or "application/json" in content_type
        or requested_with == "xmlhttprequest"
    )


def build_error_page(
    *,
    title: str,
    message: str,
    status_code: int,
    back_url: str | None = None,
) -> HTMLResponse:
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    safe_back_url = html.escape(back_url or "/")

    page = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{safe_title}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{
                background: linear-gradient(135deg, #eef4ff, #f8fbff);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: Inter, Arial, sans-serif;
            }}
            .error-card {{
                max-width: 680px;
                width: 100%;
                background: #fff;
                border-radius: 18px;
                padding: 2rem;
                box-shadow: 0 10px 32px rgba(0, 0, 0, 0.08);
            }}
            .error-code {{
                font-size: 14px;
                color: #6c757d;
                margin-bottom: .5rem;
            }}
        </style>
    </head>
    <body>
        <div class="error-card">
            <div class="error-code">Mã lỗi: {status_code}</div>
            <h2 class="text-danger fw-bold mb-3">{safe_title}</h2>
            <p class="text-muted mb-4">{safe_message}</p>
            <div class="d-flex gap-2 flex-wrap">
                <a href="{safe_back_url}" class="btn btn-primary">Quay lại</a>
                <a href="/" class="btn btn-outline-secondary">Về trang chủ</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=page, status_code=status_code)


def get_back_url(request: Request) -> str:
    referer = request.headers.get("referer")
    if referer:
        return referer
    if request.url.path.startswith("/admin"):
        return "/admin/dashboard"
    if request.url.path.startswith("/teacher"):
        return "/teacher/dashboard"
    if request.url.path.startswith("/student"):
        return "/student/dashboard"
    return "/"


# =====================================================
# GLOBAL EXCEPTION HANDLERS
# =====================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if wants_json(request):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Dữ liệu gửi lên không hợp lệ.",
                "errors": exc.errors(),
            },
        )

    return build_error_page(
        title="Dữ liệu không hợp lệ",
        message="Dữ liệu gửi lên chưa hợp lệ. Vui lòng kiểm tra lại các trường bắt buộc.",
        status_code=422,
        back_url=get_back_url(request),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if wants_json(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    if exc.status_code == 404:
        title = "Không tìm thấy nội dung"
        message = str(exc.detail or "Trang bạn cần hiện không tồn tại.")
    elif exc.status_code == 403:
        title = "Bạn không có quyền truy cập"
        message = str(exc.detail or "Bạn không được phép truy cập khu vực này.")
    elif exc.status_code == 401:
        title = "Phiên đăng nhập không hợp lệ"
        message = str(exc.detail or "Vui lòng đăng nhập lại để tiếp tục.")
    else:
        title = "Có lỗi xảy ra"
        message = str(exc.detail or "Hệ thống không thể xử lý yêu cầu này.")

    return build_error_page(
        title=title,
        message=message,
        status_code=exc.status_code,
        back_url=get_back_url(request),
    )


@app.exception_handler(TemplateNotFound)
async def template_not_found_handler(request: Request, exc: TemplateNotFound):
    traceback.print_exc()

    detail = f"Giao diện '{exc.name}' chưa được tạo hoặc đang đặt sai đường dẫn template."
    if wants_json(request):
        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "error_type": "template_not_found",
            },
        )

    return build_error_page(
        title="Thiếu giao diện hiển thị",
        message=detail,
        status_code=500,
        back_url=get_back_url(request),
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError):
    traceback.print_exc()

    detail = (
        "Không kết nối được cơ sở dữ liệu. Kiểm tra lại DB_HOST, DB_PORT, DB_USER, DB_PASS "
        "và trạng thái MySQL trước khi thao tác tiếp."
    )
    if wants_json(request):
        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "error_type": "database_unavailable",
            },
        )

    return build_error_page(
        title="Không kết nối được cơ sở dữ liệu",
        message=detail,
        status_code=500,
        back_url=get_back_url(request),
    )


@app.exception_handler(ProgrammingError)
async def programming_error_handler(request: Request, exc: ProgrammingError):
    traceback.print_exc()

    detail = (
        "Mã nguồn đang truy vấn bảng/cột không khớp với cấu trúc cơ sở dữ liệu hiện tại. "
        "Bạn cần đồng bộ lại model ORM, migration và file SQL."
    )
    if wants_json(request):
        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "error_type": "database_schema_mismatch",
            },
        )

    return build_error_page(
        title="Cấu trúc dữ liệu chưa đồng bộ",
        message=detail,
        status_code=500,
        back_url=get_back_url(request),
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    traceback.print_exc()

    detail = "Dữ liệu không hợp lệ hoặc bị trùng khóa duy nhất. Vui lòng kiểm tra lại thông tin đã nhập."
    if wants_json(request):
        return JSONResponse(
            status_code=400,
            content={
                "detail": detail,
                "error_type": "integrity_error",
            },
        )

    return build_error_page(
        title="Không thể lưu dữ liệu",
        message=detail,
        status_code=400,
        back_url=get_back_url(request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()

    if wants_json(request):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Có lỗi hệ thống xảy ra."},
        )

    return build_error_page(
        title="Có lỗi hệ thống",
        message="Hệ thống vừa gặp lỗi ngoài dự kiến. Vui lòng thử lại sau.",
        status_code=500,
        back_url=get_back_url(request),
    )


# =====================================================
# ROUTERS
# =====================================================

# Auth
from app.routers.auth.forgot_password import router as forgot_router  # noqa: E402
from app.routers.auth.login import login_router  # noqa: E402
from app.routers.auth.logout import logout_router  # noqa: E402
from app.routers.auth.register import register_router  # noqa: E402
from app.routers.auth.reset_password import router as reset_router  # noqa: E402
from app.routers.auth.social_login import router as social_login_router  # noqa: E402

# Admin
from app.routers.admin.academic_years import router as academic_year_router  # noqa: E402
from app.routers.admin.assignment import router as assignment_router  # noqa: E402
from app.routers.admin.backup_management import backup_router  # noqa: E402
from app.routers.admin.class_management import class_router  # noqa: E402
from app.routers.admin.course_category import category_router  # noqa: E402
from app.routers.admin.course_management import course_router  # noqa: E402
from app.routers.admin.course_material import router as course_material_router  # noqa: E402
from app.routers.admin.course_review import review_router  # noqa: E402
from app.routers.admin.course_section import section_router  # noqa: E402
from app.routers.admin.dashboard import dashboard_router  # noqa: E402
from app.routers.admin.discussion_management import router as discussion_router  # noqa: E402
from app.routers.admin.enrollment_management import enrollment_router  # noqa: E402

from app.routers.admin.file_storage_management import router as file_storage_management_router  # noqa: E402
from app.routers.admin.majors import router as majors_router  # noqa: E402
from app.routers.admin.module_reorder import router as module_reorder_router  # noqa: E402
from app.routers.admin.notification_management import router as notification_router  # noqa: E402
from app.routers.admin.quiz import router as quiz_router  # noqa: E402
from app.routers.admin.quiz_template import router as quiz_template_router  # noqa: E402
from app.routers.admin.report_management import report_router  # noqa: E402
from app.routers.admin.settings import router as settings_router  # noqa: E402
from app.routers.admin.statistics import statistics_router as admin_statistics_router  # noqa: E402
from app.routers.admin.teacher_management import router as teacher_router  # noqa: E402
from app.routers.admin.user_management import user_router  # noqa: E402
from app.routers.admin.wallet_admin import router as admin_wallet_router  # noqa: E402

# Teacher
from app.routers.teacher.assignment_teacher import router as teacher_assignment_router  # noqa: E402
from app.routers.teacher.class_teacher import router as teacher_class_router  # noqa: E402
from app.routers.teacher.course_teacher import router as teacher_course_router  # noqa: E402
from app.routers.teacher.lesson_teacher import router as teacher_lesson_router  # noqa: E402
from app.routers.teacher.material_teacher import router as teacher_material_router  # noqa: E402
from app.routers.teacher.message import router as teacher_message_router  # noqa: E402
from app.routers.teacher.module_teacher import router as teacher_module_router  # noqa: E402
from app.routers.teacher.profile_teacher import router as teacher_profile_router  # noqa: E402
from app.routers.teacher.quiz_teacher import router as teacher_quiz_router  # noqa: E402
from app.routers.teacher.schedule_teacher import router as teacher_schedule_router  # noqa: E402
from app.routers.teacher.teacher_dashboard import router as teacher_dashboard_router  # noqa: E402
from app.routers.teacher.teacher_notifications import router as teacher_notifications_router  # noqa: E402
from app.routers.teacher.teacher_review import router as teacher_review_router  # noqa: E402
from app.routers.teacher.teacher_statistics import router as teacher_statistics_router  # noqa: E402

# Student
from app.routers.student.assignment_student import router as student_assignment_router  # noqa: E402
from app.routers.student.cart_student import router as student_cart_router  # noqa: E402
from app.routers.student.chat_ai import router as chat_ai_router  # noqa: E402
from app.routers.student.course_student import router as student_course_router  # noqa: E402
from app.routers.student.discussion import router as student_discussion_router  # noqa: E402
from app.routers.student.lesson_student import router as student_lesson_router  # noqa: E402
from app.routers.student.material_student import router as student_material_router  # noqa: E402
from app.routers.student.message_student import router as student_message_router  # noqa: E402
from app.routers.student.notifications_student import router as student_notifications_router  # noqa: E402
from app.routers.student.profile_student import router as student_profile_router  # noqa: E402
from app.routers.student.quiz_student import router as student_quiz_router  # noqa: E402
from app.routers.student.review_student import router as student_review_router  # noqa: E402
from app.routers.student.schedule_student import router as student_schedule_router  # noqa: E402
from app.routers.student.student_dashboard import router as student_dashboard_router  # noqa: E402
from app.routers.student.wallet_student import router as student_wallet_router  # noqa: E402


for group in [
    [login_router, register_router, logout_router, forgot_router, reset_router, social_login_router],
    [
        dashboard_router,
        user_router,
        course_router,
        section_router,
        category_router,
        class_router,
        enrollment_router,
        backup_router,

        report_router,
        review_router,
        majors_router,
        academic_year_router,
        settings_router,
        admin_statistics_router,
        teacher_router,
        assignment_router,
        course_material_router,
        quiz_template_router,
        quiz_router,
        module_reorder_router,
        discussion_router,
        file_storage_management_router,
        notification_router,
        admin_wallet_router,
    ],
    [
        teacher_dashboard_router,
        teacher_course_router,
        teacher_module_router,
        teacher_lesson_router,
        teacher_material_router,
        teacher_profile_router,
        teacher_review_router,
        teacher_class_router,
        teacher_schedule_router,
        teacher_statistics_router,
        teacher_assignment_router,
        teacher_message_router,
        teacher_quiz_router,
        teacher_notifications_router,
    ],
    [
        student_dashboard_router,
        student_profile_router,
        student_course_router,
        student_lesson_router,
        student_quiz_router,
        student_assignment_router,
        student_material_router,
        student_discussion_router,
        student_review_router,
        student_schedule_router,
        student_notifications_router,
        student_message_router,
        chat_ai_router,
        student_cart_router,
        student_wallet_router,
    ],
]:
    for router in group:
        app.include_router(router)


# =====================================================
# HOME
# =====================================================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# =====================================================
# DEV SERVER
# =====================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)