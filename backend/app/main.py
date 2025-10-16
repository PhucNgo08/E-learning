import os
import traceback
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.database.connection import Base, engine
from app.models import user

# =====================================================
# 🚀 KHỞI TẠO ỨNG DỤNG
# =====================================================
app = FastAPI(
    title="E-Learning Platform",
    version="1.0.0",
    description="Hệ thống quản lý học tập trực tuyến - E-Learning"
)

# =====================================================
# ⚙️ MIDDLEWARE CẦN THIẾT
# =====================================================
# Session middleware cho login/logout
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secure-secret-key",
    session_cookie="elearn_session",
    max_age=60 * 60 * 24 * 7,  # Lưu session 7 ngày
    same_site="lax",
    https_only=False
)

# CORS (dành cho khi bạn gọi API từ frontend React hoặc AJAX)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# 📁 CẤU HÌNH TEMPLATE & STATIC
# =====================================================
from pathlib import Path

# Gốc thư mục frontend (templates + static)
FRONTEND_DIR = Path(r"D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app")

# --- STATIC CHUNG ---
ROOT_STATIC_DIR = FRONTEND_DIR / "static"
ROOT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ROOT_STATIC_DIR)), name="static")

# --- TEMPLATE CHUNG ---
ROOT_TEMPLATE_DIR = FRONTEND_DIR / "layouts" / "templates"
templates = Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR))

# --- ADMIN ---
ADMIN_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "admin"
ADMIN_STATIC_DIR = ROOT_STATIC_DIR / "admin"
ADMIN_STATIC_DIR.mkdir(parents=True, exist_ok=True)
admin_templates = Jinja2Templates(directory=str(ADMIN_TEMPLATE_DIR))
app.mount("/static/admin", StaticFiles(directory=str(ADMIN_STATIC_DIR)), name="admin_static")

# --- TEACHER ---
TEACHER_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "teacher"
TEACHER_STATIC_DIR = ROOT_STATIC_DIR / "teacher"
TEACHER_STATIC_DIR.mkdir(parents=True, exist_ok=True)
teacher_templates = Jinja2Templates(directory=str(TEACHER_TEMPLATE_DIR))
app.mount("/static/teacher", StaticFiles(directory=str(TEACHER_STATIC_DIR)), name="teacher_static")

# --- UPLOADS (ảnh, tài liệu, video do người dùng tải lên) ---
UPLOADS_DIR = Path(r"D:/KhoaHoctructuyen/KHoaHocOnline/backend/app/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# --- STUDENT ---
STUDENT_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "student"
STUDENT_STATIC_DIR = ROOT_STATIC_DIR / "student"
STUDENT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
student_templates = Jinja2Templates(directory=str(STUDENT_TEMPLATE_DIR))
app.mount("/static/student", StaticFiles(directory=str(STUDENT_STATIC_DIR)), name="student_static")

# --- Gán biến toàn cục cho tất cả template ---
for env in (
    templates.env,
    admin_templates.env,
    teacher_templates.env,
    student_templates.env,
):
    env.globals.update(now=datetime.now)


# =====================================================
# 🧭 IMPORT CÁC ROUTER
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

# --- TEACHER ---
from app.routers.teacher.teacher_dashboard import router as teacher_dashboard_router
from app.routers.teacher.course_teacher import router as teacher_course_router
from app.routers.teacher.module_teacher import router as teacher_module_router
from app.routers.teacher.lesson_teacher import router as teacher_lesson_router
from app.routers.teacher.material_teacher import router as teacher_material_router
from app.routers.teacher.profile_teacher import router as teacher_profile_router
from app.routers.teacher.teacher_review import router as teacher_review_router  # ✅ thêm review

# --- STUDENT ---
from app.routers.student.student_dashboard import router as student_dashboard_router

# =====================================================
# 🔗 KÍCH HOẠT ROUTER
# =====================================================
# Auth
app.include_router(login_router)
app.include_router(register_router)
app.include_router(logout_router)
app.include_router(forgot_router)

# Admin
app.include_router(dashboard_router)
app.include_router(user_router)
app.include_router(course_router)
app.include_router(section_router)
app.include_router(category_router)
app.include_router(class_router)
app.include_router(enrollment_router)
app.include_router(backup_router)
app.include_router(exam_router)
app.include_router(report_router)
app.include_router(review_router)
app.include_router(majors_router)
app.include_router(academic_year_router)
app.include_router(settings_router)
app.include_router(teacher_router)

# Teacher
app.include_router(teacher_dashboard_router)
app.include_router(teacher_course_router)
app.include_router(teacher_module_router)
app.include_router(teacher_lesson_router)
app.include_router(teacher_material_router)
app.include_router(teacher_profile_router)
app.include_router(teacher_review_router)

# Student
app.include_router(student_dashboard_router)

# =====================================================
# ⚙️ STARTUP EVENT
# =====================================================
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 70)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG E-LEARNING PLATFORM".center(70))
    print("=" * 70)

    # 1️⃣ Tạo bảng nếu chưa có
    try:
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"🗄️ Database connected: {engine.url.database}")
        print(f"📊 Tổng số bảng: {len(tables)} ({', '.join(tables[:6])}{'...' if len(tables)>6 else ''})")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo database: {e}")

    # 2️⃣ Kiểm tra Template & Static
    print("\n📁 KIỂM TRA TEMPLATE & STATIC")
    dirs = [
        ("Admin Templates", ADMIN_TEMPLATE_DIR),
        ("Teacher Templates", TEACHER_TEMPLATE_DIR),
        ("Student Templates", STUDENT_TEMPLATE_DIR),
        ("Root Templates", ROOT_TEMPLATE_DIR),
        ("Root Static", ROOT_STATIC_DIR)
    ]
    for name, path in dirs:
        status = "✅ Tìm thấy" if os.path.exists(path) else "❌ Thiếu"
        print(f"   • {name:<20}: {path} → {status}")

    # 3️⃣ Thống kê router
    print("\n📋 DANH SÁCH ROUTE ĐÃ KÍCH HOẠT:")
    groups = {"Auth": 0, "Admin": 0, "Teacher": 0, "Student": 0, "Khác": 0}

    for route in app.routes:
        path = route.path
        if path.startswith("/auth"):
            groups["Auth"] += 1; icon = "🔐"
        elif path.startswith("/admin"):
            groups["Admin"] += 1; icon = "🏛️"
        elif path.startswith("/teacher"):
            groups["Teacher"] += 1; icon = "👨‍🏫"
        elif path.startswith("/student"):
            groups["Student"] += 1; icon = "🎓"
        else:
            groups["Khác"] += 1; icon = "⚙️"
        print(f"   {icon} {path}")

    print("\n📦 TỔNG SỐ ROUTE:")
    for key, val in groups.items():
        print(f"   • {key:<8}: {val} routes")

    # 4️⃣ In thời gian khởi động
    now = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    print(f"\n🕓 Thời gian khởi động: {now}")
    print("=" * 70)

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
# 💓 HEALTHCHECK API
# =====================================================
@app.get("/__healthz")
def healthz():
    return {"status": "ok", "time": datetime.now().isoformat()}

# =====================================================
# 🚀 CHẠY SERVER (DEV)
# =====================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
