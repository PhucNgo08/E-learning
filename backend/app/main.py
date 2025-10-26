import os
import traceback
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect
from app.database.connection import Base, engine
from app.config.paths import UPLOADS_BASE  # ✅ dùng config chuẩn


# =====================================================
# 🚀 KHỞI TẠO ỨNG DỤNG
# =====================================================
app = FastAPI(
    title="E-Learning Platform",
    version="1.2.1",
    description="🌐 Hệ thống quản lý học tập trực tuyến - E-Learning (bản sửa lỗi session redirect)"
)

# =====================================================
# ⚙️ MIDDLEWARE
# =====================================================
app.add_middleware(
    SessionMiddleware,
    secret_key="your-secure-secret-key",
    session_cookie="elearn_session",
    max_age=60 * 60 * 24 * 7,  # cookie sống 7 ngày
    same_site="lax",
    https_only=False,
    path="/",  # ✅ cookie áp dụng toàn hệ thống
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# 📁 TEMPLATE & STATIC FILES
# =====================================================
FRONTEND_DIR = Path(r"D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app")

ROOT_STATIC_DIR = FRONTEND_DIR / "static"
ROOT_STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(ROOT_STATIC_DIR)), name="static")

ROOT_TEMPLATE_DIR = FRONTEND_DIR / "layouts" / "templates"
templates = Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR))

ADMIN_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "admin"
TEACHER_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "teacher"
STUDENT_TEMPLATE_DIR = ROOT_TEMPLATE_DIR / "student"

admin_templates = Jinja2Templates(directory=str(ADMIN_TEMPLATE_DIR))
teacher_templates = Jinja2Templates(directory=str(TEACHER_TEMPLATE_DIR))
student_templates = Jinja2Templates(directory=str(STUDENT_TEMPLATE_DIR))

# === STATIC PHÂN NHÁNH (admin / teacher / student) ===
for name in ["admin", "teacher", "student"]:
    static_dir = ROOT_STATIC_DIR / name
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount(f"/static/{name}", StaticFiles(directory=str(static_dir)), name=f"{name}_static")

# =====================================================
# 🎨 LAYOUT STYLES (CSS)
# =====================================================
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

# =====================================================
# 📦 UPLOADS (BACKEND/APP/UPLOADS)
# =====================================================
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_BASE)), name="uploads")

print("\n✅ ĐÃ CẤU HÌNH UPLOADS:")
for folder in os.listdir(UPLOADS_BASE):
    print(f"   • {folder:<20}: {UPLOADS_BASE / folder}")

# =====================================================
# 🖼️ ẢNH FALLBACK CHO AVATAR MẶC ĐỊNH
# =====================================================
DEFAULT_AVATAR_PATH = UPLOADS_BASE / "avatars" / "default-avatar.png"

# 🔧 Nếu file không tồn tại → tự tạo ảnh mặc định
if not DEFAULT_AVATAR_PATH.exists():
    try:
        from PIL import Image, ImageDraw
        DEFAULT_AVATAR_PATH.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (256, 256), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.ellipse((70, 40, 190, 160), fill=(200, 200, 200))
        draw.rectangle((100, 160, 160, 240), fill=(200, 200, 200))
        img.save(DEFAULT_AVATAR_PATH)
        print(f"🖼️ Đã tạo avatar mặc định: {DEFAULT_AVATAR_PATH}")
    except Exception as e:
        print(f"⚠️ Không thể tạo avatar mặc định: {e}")

# ✅ Route phục vụ avatar (có fallback)
@app.get("/uploads/avatars/{filename}")
async def serve_avatar(filename: str):
    avatar_path = UPLOADS_BASE / "avatars" / filename
    if not avatar_path.exists():
        return FileResponse(DEFAULT_AVATAR_PATH)
    return FileResponse(avatar_path)

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
from app.routers.teacher.message import router as teacher_message_router
from app.routers.teacher.quiz_teacher import router as teacher_quiz_router
from app.routers.teacher.teacher_notifications import router as teacher_notifications_router

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
# 🔗 ĐĂNG KÝ ROUTER
# =====================================================
for routers in [
    [login_router, register_router, logout_router, forgot_router],
    
    [dashboard_router, user_router, course_router, section_router, category_router,
     class_router, enrollment_router, backup_router, exam_router, report_router,
     review_router, majors_router, academic_year_router, settings_router, teacher_router,
     assignment.router, course_material.router, quiz_template.router, quiz.router, module_reorder.router],


    [teacher_dashboard_router, teacher_course_router, teacher_module_router, teacher_lesson_router,
     teacher_material_router, teacher_profile_router, teacher_review_router, teacher_class_router,
     teacher_schedule_router, teacher_statistics_router, teacher_assignment_router, teacher_message_router,
     teacher_quiz_router, teacher_notifications_router],


    [student_dashboard_router, student_profile_router, student_course_router, student_lesson_router,
     student_quiz_router, student_assignment_router, student_material_router, student_discussion_router,
     student_review_router, student_schedule_router, student_notifications_router, student_message_router]
]:
    for r in routers:
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
        count_info = ""
        if exists:
            try:
                items = len([f for f in os.listdir(path) if not f.startswith('.')])
                count_info = f"({items} mục)"
            except Exception:
                count_info = ""
        print(f"   • {name:<20}: {path} → {status} {count_info}")

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
