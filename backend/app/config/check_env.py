import os
import sys
from pathlib import Path
import platform
import importlib.util
from datetime import datetime

# =====================================================
# 🔍 TỰ ĐỘNG PHÁT HIỆN THƯ MỤC BACKEND
# =====================================================
def find_backend_dir(start_path: Path) -> Path:
    """
    Dò ngược lên trên để tìm thư mục 'backend'
    (nếu không tìm thấy thì trả về thư mục hiện tại)
    """
    for parent in start_path.resolve().parents:
        if (parent / "backend").exists():
            return parent / "backend"
        # Trường hợp đang chạy ngay trong backend
        if (parent / "app").exists() and (parent / "requirements.txt").exists():
            return parent
    return start_path  # fallback

# === Xác định vị trí gốc backend ===
CURRENT_PATH = Path(__file__).resolve()
BACKEND_DIR = find_backend_dir(CURRENT_PATH)
APP_DIR = BACKEND_DIR / "app"
FRONTEND_DIR = BACKEND_DIR.parent / "frontend" / "react-app"
UPLOADS_DIR = APP_DIR / "uploads"
TEMPLATES_DIR = FRONTEND_DIR / "layouts" / "templates"

# === Tạo thư mục logs (nếu chưa có) ===
LOGS_DIR = BACKEND_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "env_check.log"


# =====================================================
# 🧾 GHI LOG RA CONSOLE + FILE
# =====================================================
def log_write(message: str):
    print(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


# =====================================================
# 🧠 KIỂM TRA MÔI TRƯỜNG
# =====================================================
log_write("=" * 90)
log_write("🔍 KIỂM TRA MÔI TRƯỜNG HỆ THỐNG E-LEARNING PLATFORM".center(90))
log_write("=" * 90)

log_write(f"🖥️  Hệ điều hành  : {platform.system()} {platform.release()}")
log_write(f"🐍  Python version: {sys.version.split()[0]}")
log_write(f"📅  Thời gian kiểm tra: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}")
log_write("-" * 90)
log_write(f"📂 File đang chạy : {CURRENT_PATH}")
log_write(f"📂 BACKEND_DIR     : {BACKEND_DIR}")
log_write("-" * 90)


# =====================================================
# 📁 KIỂM TRA CẤU TRÚC THƯ MỤC
# =====================================================
def check_exists(path: Path, name: str):
    if path.exists():
        log_write(f"✅ {name:<25}: {path}")
        return True
    else:
        log_write(f"❌ {name:<25}: {path} (không tồn tại)")
        return False


log_write("📁 KIỂM TRA CẤU TRÚC THƯ MỤC:")
check_exists(APP_DIR, "Thư mục backend/app")
check_exists(UPLOADS_DIR, "Thư mục uploads")
check_exists(TEMPLATES_DIR, "Thư mục templates")
check_exists(FRONTEND_DIR / "static", "Thư mục static")
check_exists(FRONTEND_DIR / "layouts" / "styles", "Thư mục styles")
log_write("-" * 90)


# =====================================================
# 🗂️ KIỂM TRA UPLOAD CON
# =====================================================
EXPECTED_UPLOADS = ["avatars", "course_thumbnails", "materials", "videos", "messages"]
log_write("🗂️ KIỂM TRA THƯ MỤC UPLOAD CON:")
if UPLOADS_DIR.exists():
    missing = [sub for sub in EXPECTED_UPLOADS if not (UPLOADS_DIR / sub).exists()]
    if missing:
        log_write(f"⚠️  Thiếu các thư mục upload con: {', '.join(missing)}")
    else:
        log_write("✅ Tất cả thư mục upload con đã tồn tại đầy đủ.")
else:
    log_write("❌ Thư mục uploads không tồn tại.")
log_write("-" * 90)


# =====================================================
# 🎨 KIỂM TRA TEMPLATE CON
# =====================================================
EXPECTED_TEMPLATES = ["admin", "teacher", "student", "auth"]
log_write("🎨 KIỂM TRA TEMPLATE CON:")
if TEMPLATES_DIR.exists():
    missing = [t for t in EXPECTED_TEMPLATES if not (TEMPLATES_DIR / t).exists()]
    if missing:
        log_write(f"⚠️  Thiếu các thư mục template con: {', '.join(missing)}")
    else:
        log_write("✅ Tất cả thư mục template con đầy đủ.")
else:
    log_write("❌ Thư mục templates không tồn tại.")
log_write("-" * 90)


# =====================================================
# 📦 KIỂM TRA FILE QUAN TRỌNG
# =====================================================
log_write("📦 KIỂM TRA FILE QUAN TRỌNG:")
check_exists(BACKEND_DIR / ".env", "File .env")
check_exists(BACKEND_DIR / "requirements.txt", "File requirements.txt")
check_exists(BACKEND_DIR / "alembic.ini", "File alembic.ini")
check_exists(APP_DIR / "main.py", "File main.py")
log_write("-" * 90)


# =====================================================
# 🐍 KIỂM TRA PACKAGE PYTHON
# =====================================================
REQUIRED_PACKAGES = ["fastapi", "uvicorn", "sqlalchemy", "jinja2", "python-multipart"]
log_write("🐍 KIỂM TRA GÓI PYTHON CẦN THIẾT:")
for pkg in REQUIRED_PACKAGES:
    if importlib.util.find_spec(pkg) is None:
        log_write(f"❌ Thiếu package: {pkg}")
    else:
        log_write(f"✅ Package sẵn sàng: {pkg}")
log_write("-" * 90)


# =====================================================
# 📊 TỔNG KẾT
# =====================================================
log_write("📊 TỔNG KẾT KIỂM TRA:")
ok = (
    APP_DIR.exists()
    and UPLOADS_DIR.exists()
    and TEMPLATES_DIR.exists()
    and all((UPLOADS_DIR / sub).exists() for sub in EXPECTED_UPLOADS)
)
if ok:
    log_write("🎉 Môi trường sẵn sàng để chạy E-Learning Platform!")
    log_write("👉 Bạn có thể chạy: uvicorn app.main:app --reload")
else:
    log_write("⚠️ Môi trường CHƯA SẴN SÀNG — cần kiểm tra lại cấu trúc hoặc cài đặt phụ thuộc.")
log_write("=" * 90)

print(f"\n📝 Log đã được ghi tại: {LOG_FILE}\n")
