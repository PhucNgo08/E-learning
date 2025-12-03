import os
import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Database
from app.database.connection import Base, engine
from app.config.paths import UPLOADS_BASE


# =====================================================
# 🚀 FASTAPI APP
# =====================================================
app = FastAPI(
    title="E-Learning Platform",
    version="1.2.3",
    description="🌐 Hệ thống quản lý học tập trực tuyến - FastAPI",
)


# =====================================================
# ⚙️ MIDDLEWARE
# =====================================================

app.add_middleware(
    SessionMiddleware,
    secret_key="super-secure-key-123456789-ABCDEF-XYZ",
    session_cookie="elearn_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)

from app.middleware.session_expire_checker import SessionExpireMiddleware
app.add_middleware(SessionExpireMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# 📁 STATIC & TEMPLATE SETUP — FIX CHUẨN V10
# =====================================================

# project/
#   backend/app/main.py   → cần đi lên 3 cấp
ROOT = Path(__file__).resolve().parent.parent.parent

FRONTEND_DIR = ROOT / "frontend" / "react-app"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATE_DIR = FRONTEND_DIR / "layouts" / "templates"
STYLE_DIR = FRONTEND_DIR / "layouts" / "styles"

print("📌 STATIC_DIR =", STATIC_DIR)
print("📌 TEMPLATE_DIR =", TEMPLATE_DIR)

# --- Mount Static ---
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/frontend/react-app/layouts/styles", StaticFiles(directory=str(STYLE_DIR)), name="styles")

# --- Templates ---
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.templates = templates
app.admin_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "admin"))
app.teacher_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "teacher"))
app.student_templates = Jinja2Templates(directory=str(TEMPLATE_DIR / "student"))

# Inject global variable "now"
for env in [
    templates.env,
    app.admin_templates.env,
    app.teacher_templates.env,
    app.student_templates.env,
]:
    env.globals.update(now=datetime.now)


# =====================================================
# 📦 UPLOADS
# =====================================================
if UPLOADS_BASE.exists():
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_BASE)), name="uploads")
else:
    print("⚠️ UPLOADS directory missing:", UPLOADS_BASE)


DEFAULT_AVATAR_PATH = UPLOADS_BASE / "avatars" / "default-avatar.png"


@app.get("/uploads/avatars/{filename}")
async def serve_avatar(filename: str):
    avatar_path = UPLOADS_BASE / "avatars" / filename
    if avatar_path.exists():
        return FileResponse(avatar_path)
    return FileResponse(DEFAULT_AVATAR_PATH)


# =====================================================
# 📡 ROUTERS (KEEP ORIGINAL)
# =====================================================

# ... (toàn bộ phần routers giữ nguyên, không thay đổi)

from app.routers.auth.login import login_router
from app.routers.auth.register import register_router
from app.routers.auth.logout import logout_router
from app.routers.auth.forgot_password import router as forgot_router
from app.routers.auth.reset_password import router as reset_router
from app.routers.auth.social_login import router as social_login_router

from app.routers.admin.dashboard import dashboard_router
from app.routers.admin.user_management import user_router
from app.routers.admin.course_management import course_router
from app.routers.admin.course_section import section_router
from app.routers.admin.course_category import category_router
from app.routers.admin.class_management import class_router
from app.routers.admin.enrollment_management import enrollment_router
from app.routers.admin.backup_management import backup_router
from app.routers.admin.exam_management import exam_router
from app.routers.admin.report_management import report_router
from app.routers.admin.course_review import review_router
from app.routers.admin.academic_years import router as academic_year_router
from app.routers.admin.settings import router as settings_router
from app.routers.admin.majors import router as majors_router
from app.routers.admin.teacher_management import router as teacher_router
from app.routers.admin import assignment, course_material, quiz_template, quiz, module_reorder
from app.routers.admin import discussion, file_storage_management, notification
from app.routers.admin.wallet_admin import router as admin_wallet_router

from app.routers.teacher.teacher_dashboard import router as teacher_dashboard_router
from app.routers.teacher.course_teacher import router as teacher_course_router
from app.routers.teacher.module_teacher import router as teacher_module_router
from app.routers.teacher.lesson_teacher import router as teacher_lesson_router
from app.routers.teacher.material_teacher import router as teacher_material_router
from app.routers.teacher.profile_teacher import router as teacher_profile_router
from app.routers.teacher.teacher_review import router as teacher_review_router
from app.routers.teacher.class_teacher import router as teacher_class_router
from app.routers.teacher.schedule_teacher import router as teacher_schedule_router
from app.routers.teacher.teacher_statistics import router as teacher_statistics_router
from app.routers.teacher.assignment_teacher import router as teacher_assignment_router
from app.routers.teacher.message import router as teacher_message_router
from app.routers.teacher.quiz_teacher import router as teacher_quiz_router
from app.routers.teacher.teacher_notifications import router as teacher_notifications_router

from app.routers.student.student_dashboard import router as student_dashboard_router
from app.routers.student.profile_student import router as student_profile_router
from app.routers.student.course_student import router as student_course_router
from app.routers.student.lesson_student import router as student_lesson_router
from app.routers.student.quiz_student import router as student_quiz_router
from app.routers.student.assignment_student import router as student_assignment_router
from app.routers.student.material_student import router as student_material_router
from app.routers.student.discussion import router as student_discussion_router
from app.routers.student.review_student import router as student_review_router
from app.routers.student.schedule_student import router as student_schedule_router
from app.routers.student.notifications_student import router as student_notifications_router
from app.routers.student.message_student import router as student_message_router
from app.routers.student import chat_ai
from app.routers.student.cart_student import router as student_cart_router
from app.routers.student.wallet_student import router as student_wallet_router

for group in [
    [login_router, register_router, logout_router, forgot_router, reset_router, social_login_router],
    [dashboard_router, user_router, course_router, section_router, category_router, class_router,
     enrollment_router, backup_router, exam_router, report_router, review_router, majors_router,
     academic_year_router, settings_router, teacher_router,
     assignment.router, course_material.router, quiz_template.router, quiz.router,
     module_reorder.router, discussion.router, file_storage_management.router,
     notification.router, admin_wallet_router],
    [teacher_dashboard_router, teacher_course_router, teacher_module_router, teacher_lesson_router,
     teacher_material_router, teacher_profile_router, teacher_review_router, teacher_class_router,
     teacher_schedule_router, teacher_statistics_router, teacher_assignment_router,
     teacher_message_router, teacher_quiz_router, teacher_notifications_router],
    [student_dashboard_router, student_profile_router, student_course_router, student_lesson_router,
     student_quiz_router, student_assignment_router, student_material_router,
     student_discussion_router, student_review_router, student_schedule_router,
     student_notifications_router, student_message_router, chat_ai.router,
     student_cart_router, student_wallet_router]
]:
    for r in group:
        app.include_router(r)


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
