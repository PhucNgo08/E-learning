import sys
import platform
import importlib.util
from pathlib import Path
from datetime import datetime

# =====================================================
# 🔍 TỰ ĐỘNG PHÁT HIỆN THƯ MỤC BACKEND
# =====================================================
def find_backend_dir(start_path: Path) -> Path:
    """
    Dò ngược lên trên để tìm thư mục backend.

    Hỗ trợ 2 trường hợp:
    1. File đang nằm trong backend/app/config/check_env.py
    2. Chạy script từ vị trí khác nhưng nằm trong project
    """
    current = start_path.resolve()

    # Nếu chính thư mục hiện tại hoặc cha của nó là backend
    for parent in [current.parent, *current.parents]:
        if parent.name.lower() == "backend" and (parent / "app").exists():
            return parent

        # Nếu parent chứa thư mục backend
        if (parent / "backend").exists() and (parent / "backend" / "app").exists():
            return parent / "backend"

        # Nếu parent là backend nhưng không đặt tên backend
        if (parent / "app").exists() and (parent / "requirements.txt").exists():
            return parent

    return current.parent


# =====================================================
# 📌 XÁC ĐỊNH ĐƯỜNG DẪN CHÍNH
# =====================================================
CURRENT_PATH = Path(__file__).resolve()
BACKEND_DIR = find_backend_dir(CURRENT_PATH)
PROJECT_DIR = BACKEND_DIR.parent

APP_DIR = BACKEND_DIR / "app"
FRONTEND_DIR = PROJECT_DIR / "frontend" / "react-app"
UPLOADS_DIR = APP_DIR / "uploads"
TEMPLATES_DIR = FRONTEND_DIR / "layouts" / "templates"
STATIC_DIR = FRONTEND_DIR / "static"
STYLES_DIR = FRONTEND_DIR / "layouts" / "styles"

LOGS_DIR = BACKEND_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "env_check.log"


# =====================================================
# 🧾 GHI LOG RA CONSOLE + FILE
# =====================================================
def log_write(message: str = "") -> None:
    print(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def reset_log_file() -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")


# =====================================================
# ✅ HÀM KIỂM TRA CHUNG
# =====================================================
def check_exists(path: Path, name: str) -> bool:
    if path.exists():
        log_write(f"✅ {name:<28}: {path}")
        return True

    log_write(f"❌ {name:<28}: {path} (không tồn tại)")
    return False


def check_python_package(package_name: str, import_name: str) -> bool:
    """
    package_name: tên cài bằng pip, ví dụ python-multipart
    import_name : tên import trong Python, ví dụ multipart
    """
    if importlib.util.find_spec(import_name) is None:
        log_write(f"❌ Thiếu package: {package_name}")
        log_write(f"   👉 Cài bằng: py -m pip install {package_name}")
        return False

    log_write(f"✅ Package sẵn sàng: {package_name}")
    return True


# =====================================================
# 🚀 BẮT ĐẦU KIỂM TRA
# =====================================================
reset_log_file()

log_write("=" * 90)
log_write("🔍 KIỂM TRA MÔI TRƯỜNG HỆ THỐNG E-LEARNING PLATFORM".center(90))
log_write("=" * 90)

log_write(f"🖥️  Hệ điều hành      : {platform.system()} {platform.release()}")
log_write(f"🐍  Python version    : {sys.version.split()[0]}")
log_write(f"📅  Thời gian kiểm tra: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}")
log_write("-" * 90)
log_write(f"📂 File đang chạy     : {CURRENT_PATH}")
log_write(f"📂 PROJECT_DIR        : {PROJECT_DIR}")
log_write(f"📂 BACKEND_DIR        : {BACKEND_DIR}")
log_write(f"📂 FRONTEND_DIR       : {FRONTEND_DIR}")
log_write("-" * 90)


# =====================================================
# 📁 KIỂM TRA CẤU TRÚC THƯ MỤC
# =====================================================
log_write("📁 KIỂM TRA CẤU TRÚC THƯ MỤC:")

folder_checks = [
    check_exists(APP_DIR, "Thư mục backend/app"),
    check_exists(UPLOADS_DIR, "Thư mục uploads"),
    check_exists(TEMPLATES_DIR, "Thư mục templates"),
    check_exists(STATIC_DIR, "Thư mục static"),
    check_exists(STYLES_DIR, "Thư mục styles"),
]

log_write("-" * 90)


# =====================================================
# 🗂️ KIỂM TRA THƯ MỤC UPLOAD CON
# =====================================================
EXPECTED_UPLOADS = [
    "avatars",
    "course_thumbnails",
    "materials",
    "videos",
    "messages",
]

log_write("🗂️ KIỂM TRA THƯ MỤC UPLOAD CON:")

upload_checks = []

if UPLOADS_DIR.exists():
    for sub in EXPECTED_UPLOADS:
        sub_path = UPLOADS_DIR / sub
        if sub_path.exists():
            log_write(f"✅ Upload/{sub:<20}: {sub_path}")
            upload_checks.append(True)
        else:
            log_write(f"❌ Upload/{sub:<20}: {sub_path} (không tồn tại)")
            log_write(f"   👉 Tạo bằng: mkdir {sub_path}")
            upload_checks.append(False)
else:
    log_write("❌ Không thể kiểm tra upload con vì thư mục uploads không tồn tại.")
    upload_checks.append(False)

log_write("-" * 90)


# =====================================================
# 🎨 KIỂM TRA TEMPLATE CON
# =====================================================
EXPECTED_TEMPLATES = [
    "admin",
    "teacher",
    "student",
    "auth",
]

log_write("🎨 KIỂM TRA TEMPLATE CON:")

template_checks = []

if TEMPLATES_DIR.exists():
    for sub in EXPECTED_TEMPLATES:
        sub_path = TEMPLATES_DIR / sub
        if sub_path.exists():
            log_write(f"✅ Template/{sub:<18}: {sub_path}")
            template_checks.append(True)
        else:
            log_write(f"❌ Template/{sub:<18}: {sub_path} (không tồn tại)")
            template_checks.append(False)
else:
    log_write("❌ Không thể kiểm tra template con vì thư mục templates không tồn tại.")
    template_checks.append(False)

log_write("-" * 90)


# =====================================================
# 📦 KIỂM TRA FILE QUAN TRỌNG
# =====================================================
log_write("📦 KIỂM TRA FILE QUAN TRỌNG:")

file_checks = [
    check_exists(BACKEND_DIR / ".env", "File .env"),
    check_exists(BACKEND_DIR / "requirements.txt", "File requirements.txt"),
    check_exists(BACKEND_DIR / "alembic.ini", "File alembic.ini"),
    check_exists(APP_DIR / "main.py", "File main.py"),
]

log_write("-" * 90)


# =====================================================
# 🧪 KIỂM TRA .ENV CƠ BẢN
# =====================================================
log_write("🧪 KIỂM TRA BIẾN MÔI TRƯỜNG TRONG .env:")

env_checks = []
env_path = BACKEND_DIR / ".env"

required_env_keys = [
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASS",
    "DB_NAME",
    "SESSION_SECRET_KEY",
]

if env_path.exists():
    env_content = env_path.read_text(encoding="utf-8", errors="ignore")

    for key in required_env_keys:
        has_key = any(
            line.strip().startswith(f"{key}=")
            for line in env_content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

        if has_key:
            log_write(f"✅ Biến .env tồn tại: {key}")
            env_checks.append(True)
        else:
            log_write(f"❌ Thiếu biến .env: {key}")
            env_checks.append(False)

    if "DB_PASSWORD=" in env_content and "DB_PASS=" not in env_content:
        log_write("⚠️  Phát hiện DB_PASSWORD nhưng code thường đọc DB_PASS.")
        log_write("   👉 Nên đổi DB_PASSWORD thành DB_PASS trong file .env.")
        env_checks.append(False)

else:
    log_write("❌ Không kiểm tra được .env vì file .env không tồn tại.")
    env_checks.append(False)

log_write("-" * 90)


# =====================================================
# 🐍 KIỂM TRA PACKAGE PYTHON
# =====================================================
log_write("🐍 KIỂM TRA GÓI PYTHON CẦN THIẾT:")

# Key là tên cài bằng pip, value là tên import trong Python
REQUIRED_PACKAGES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "jinja2": "jinja2",
    "python-multipart": "multipart",
    "pydantic": "pydantic",
    "starlette": "starlette",
    "dotenv": "dotenv",
}

package_checks = [
    check_python_package(package_name, import_name)
    for package_name, import_name in REQUIRED_PACKAGES.items()
]

log_write("-" * 90)


# =====================================================
# 📊 TỔNG KẾT
# =====================================================
all_checks = (
    folder_checks
    + upload_checks
    + template_checks
    + file_checks
    + env_checks
    + package_checks
)

passed_count = sum(1 for item in all_checks if item)
failed_count = sum(1 for item in all_checks if not item)

log_write("📊 TỔNG KẾT KIỂM TRA:")
log_write(f"✅ Số mục đạt    : {passed_count}")
log_write(f"❌ Số mục lỗi    : {failed_count}")

if failed_count == 0:
    log_write("🎉 Môi trường sẵn sàng để chạy E-Learning Platform!")
    log_write("👉 Chạy server bằng lệnh:")
    log_write("   py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
else:
    log_write("⚠️ Môi trường CHƯA SẴN SÀNG hoàn toàn.")
    log_write("👉 Hãy sửa các dòng có dấu ❌ ở trên rồi chạy lại:")
    log_write("   py -m app.config.check_env")

log_write("=" * 90)
log_write(f"📝 Log đã được ghi tại: {LOG_FILE}")

print(f"\n📝 Log đã được ghi tại: {LOG_FILE}\n")