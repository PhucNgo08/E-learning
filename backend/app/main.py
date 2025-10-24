import os
import traceback
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.database.connection import Base, engine

# =====================================================
# 🚀 KHỞI TẠO ỨNG DỤNG
# =====================================================
app = FastAPI(
    title="E-Learning Platform",
    version="1.2.0",
    description="🌐 Hệ thống quản lý học tập trực tuyến - E-Learning (bản đa nền tảng & tự động cấu hình)"
)

# =====================================================
# ⚙️ MIDDLEWARE
# =====================================================
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secure-secret-key",
    session_cookie="elearn_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# 📁 CẤU HÌNH ĐƯỜNG DẪN TỰ ĐỘNG (TƯƠNG THÍCH MỌI MÁY)
# =====================================================
# Lấy thư mục gốc dự án (gồm backend + frontend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# FRONTEND & BACKEND PATHS
FRONTEND_DIR = BASE_DIR / "frontend" / "react-app"
BACKEND_DIR = BASE_DIR / "backend" / "app"

# --- STATIC CHUNG ---
ROOT_STATIC_DIR = FRONTEND_DIR / "static"
ROOT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ROOT_STATIC_DIR)), name="static")

# --- TEMPLATE CHUNG ---
ROOT_TEMPLATE_DIR = FRONTEND_DIR / "layouts" / "templates"
templates = Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR))

# --- TEMPLATE RIÊNG ---
ADMIN_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "admin"
TEACHER_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "teacher"
STUDENT_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "student"

admin_templates = Jinja2Templates(directory=str(ADMIN_TEMPLATE_DIR))
teacher_templates = Jinja2Templates(directory=str(TEACHER_TEMPLATE_DIR))
student_templates = Jinja2Templates(directory=str(STUDENT_TEMPLATE_DIR))

# --- STATIC PHÂN NHÁNH ---
for name in ["admin", "teacher", "student"]:
    static_dir = ROOT_STATIC_DIR / name
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount(f"/static/{name}", StaticFiles(directory=str(static_dir)), name=f"{name}_static")

# --- LAYOUT STYLES ---
LAYOUT_STYLES_DIR = FRONTEND_DIR / "layouts" / "styles"
if LAYOUT_STYLES_DIR.exists():
    app.mount(
        "/frontend/react-app/layouts/styles",
        StaticFiles(directory=str(LAYOUT_STYLES_DIR)),
        name="layout_styles"
    )
    print(f"✅ Mounted layout styles: {LAYOUT_STYLES_DIR}")
else:
    print(f"⚠️ Layout styles folder không tồn tại: {LAYOUT_STYLES_DIR}")

# --- UPLOADS ---
UPLOADS_BASE = BACKEND_DIR / "uploads"
UPLOADS_BASE.mkdir(parents=True, exist_ok=True)

UPLOAD_DIRS = {
    "course_thumbnails": UPLOADS_BASE / "course_thumbnails",
    "avatars": UPLOADS_BASE / "avatars",
    "materials": UPLOADS_BASE / "materials",
    "videos": UPLOADS_BASE / "videos",
}

for name, path in UPLOAD_DIRS.items():
    path.mkdir(parents=True, exist_ok=True)
    app.mount(f"/uploads/{name}", StaticFiles(directory=str(path)), name=name)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_BASE)), name="uploads")

print("\n✅ ĐÃ CẤU HÌNH UPLOADS:")
for key, val in UPLOAD_DIRS.items():
    print(f"   • {key:<20}: {val}")

# =====================================================
# 🌍 BIẾN TOÀN CỤC TEMPLATE
# =====================================================
for env in (templates.env, admin_templates.env, teacher_templates.env, student_templates.env):
    env.globals.update(now=datetime.now)

# =====================================================
# 🧭 IMPORT ROUTER
# =====================================================
# --- AUTH ---
from app.routers.auth.login import login_router
from app.routers.auth.register import register_router
from app.routers.auth.logout import logout_router
from app.routers.auth.forgot_password import router as forgot_router

# --- ADMIN ---
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

# --- TEACHER ---
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

# --- STUDENT ---
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

# =====================================================
# 🔗 KÍCH HOẠT ROUTER
# =====================================================
# Auth
for r in [login_router, register_router, logout_router, forgot_router]:
    app.include_router(r)

# Admin
for r in [
    dashboard_router, user_router, course_router, section_router, category_router,
    class_router, enrollment_router, backup_router, exam_router, report_router,
    review_router, majors_router, academic_year_router, settings_router, teacher_router,
    assignment.router, course_material.router, quiz_template.router, quiz.router, module_reorder.router
]:
    app.include_router(r)

# Teacher
for r in [
    teacher_dashboard_router, teacher_course_router, teacher_module_router,
    teacher_lesson_router, teacher_material_router, teacher_profile_router,
    teacher_review_router, teacher_class_router, teacher_schedule_router,
    teacher_statistics_router, teacher_assignment_router
]:
    app.include_router(r)

# Student
for r in [
    student_dashboard_router, student_profile_router, student_course_router,
    student_lesson_router, student_quiz_router, student_assignment_router,
    student_material_router, student_discussion_router, student_review_router,
    student_schedule_router, student_notifications_router, student_message_router
]:
    app.include_router(r)

# =====================================================
# ⚙️ STARTUP EVENT
# =====================================================
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 85)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG E-LEARNING PLATFORM".center(85))
    print("=" * 85)

    try:
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"🗄️ Database connected: {engine.url.database}")
        print(f"📊 Tổng số bảng: {len(tables)}")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo database: {e}")

    # --- KIỂM TRA THƯ MỤC ---
    print("\n📁 KIỂM TRA TEMPLATE & STATIC:")
    dirs = [
        ("Admin Templates", ADMIN_TEMPLATE_DIR),
        ("Teacher Templates", TEACHER_TEMPLATE_DIR),
        ("Student Templates", STUDENT_TEMPLATE_DIR),
        ("Root Templates", ROOT_TEMPLATE_DIR),
        ("Layout Styles", LAYOUT_STYLES_DIR),
        ("Root Static", ROOT_STATIC_DIR),
        ("Admin Static", ROOT_STATIC_DIR / "admin"),
        ("Teacher Static", ROOT_STATIC_DIR / "teacher"),
        ("Student Static", ROOT_STATIC_DIR / "student"),
        ("Uploads", UPLOADS_BASE),
    ]
    for name, path in dirs:
        exists = os.path.exists(path)
        status = "✅ OK" if exists else "❌ Thiếu"
        try:
            count = len([f for f in os.listdir(path)]) if exists else 0
        except Exception:
            count = 0
        print(f"   • {name:<20}: {path} → {status} ({count} mục)")

    # --- THỐNG KÊ ROUTES ---
    print("\n📦 ROUTES ĐÃ ĐĂNG KÝ:")
    groups = {"Auth": 0, "Admin": 0, "Teacher": 0, "Student": 0, "Khác": 0}
    for route in app.routes:
        path = route.path
        if path.startswith("/auth"): groups["Auth"] += 1; icon = "🔐"
        elif path.startswith("/admin"): groups["Admin"] += 1; icon = "🏛️"
        elif path.startswith("/teacher"): groups["Teacher"] += 1; icon = "👨‍🏫"
        elif path.startswith("/student"): groups["Student"] += 1; icon = "🎓"
        else: groups["Khác"] += 1; icon = "⚙️"
        print(f"   {icon} {path}")

    total = sum(groups.values())
    print("\n📊 TỔNG HỢP ROUTES:")
    for k, v in groups.items():
        print(f"   • {k:<10}: {v:>3} route")
    print(f"   🧩 Tổng cộng : {total} route")
    print(f"\n🕓 Thời gian khởi động: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}")
    print("=" * 85)

# =====================================================
# 🏠 TRANG CHỦ
# =====================================================
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        return templates.TemplateResponse("home.html", {"request": request})
    except Exception:
        print("\n❌ LỖI TRANG CHỦ:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =====================================================
# 💓 HEALTHCHECK
# =====================================================
@app.get("/__healthz")
def healthz():
    return {"status": "ok", "time": datetime.now().isoformat()}

# =====================================================
# 🚀 DEV SERVER
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
