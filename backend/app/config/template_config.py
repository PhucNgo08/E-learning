from pathlib import Path
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import os

# ==========================================================
# 🌍 TEMPLATE CONFIGURATION - DÙNG CHUNG CHO ADMIN / TEACHER / STUDENT / AUTH
# ==========================================================

# ✅ BASE_DIR: Thư mục gốc của dự án
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# ✅ ROOT_TEMPLATE_DIR: chứa toàn bộ template HTML
ROOT_TEMPLATE_DIR = BASE_DIR / "frontend" / "react-app" / "layouts" / "templates"

# ==========================================================
# 🧩 DEBUG THÔNG TIN ĐƯỜNG DẪN (chỉ in 1 lần)
# ==========================================================
if not os.environ.get("TEMPLATE_LOGGED"):
    os.environ["TEMPLATE_LOGGED"] = "1"
    print("=" * 90)
    print("📁 [TEMPLATE CONFIG] Root template dir:", ROOT_TEMPLATE_DIR)
    print("📂 Template directory exists:", ROOT_TEMPLATE_DIR.exists())
    print("📂 Exists student/course/list.html:",
          (ROOT_TEMPLATE_DIR / "student" / "course" / "list.html").exists())
    print("=" * 90)

# ==========================================================
# 🧱 KHỞI TẠO TEMPLATE CHO TỪNG NHÓM (Admin / Teacher / Student / Auth / Root)
# ==========================================================
templates = {
    "admin": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "admin")),
    "teacher": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "teacher")),
    "student": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "student")),
    "auth": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "auth")),
    "root": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR)),  # cho trang index
}

# ==========================================================
# 🌟 BIẾN TOÀN CỤC DÙNG CHUNG
# ==========================================================
for name, tpl in templates.items():
    tpl.env.globals.update({
        # ✅ now() → {{ now().strftime('%H:%M - %d/%m/%Y') }}
        "now": lambda: datetime.utcnow() + timedelta(hours=7),
        # ✅ year → {{ year }}
        "year": (datetime.utcnow() + timedelta(hours=7)).year,
        "app_name": f"E-Learning Platform ({name.capitalize()})",
        "version": "1.0.0",
        "company": "Online Education Team",
        "base_url": "/",
    })

# ==========================================================
# 🧮 FILTER DÙNG CHUNG
# ==========================================================
def filesize_fmt(value: int):
    """Định dạng kích thước file (B, KB, MB, GB)."""
    if not value:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def datetime_fmt(value: datetime):
    """Định dạng ngày giờ theo múi giờ VN (UTC+7)."""
    if not value:
        return ""
    return (value + timedelta(hours=7)).strftime("%H:%M - %d/%m/%Y")


# Đăng ký filter cho tất cả template
for tpl in templates.values():
    tpl.env.filters["filesize"] = filesize_fmt
    tpl.env.filters["datetime"] = datetime_fmt

# ==========================================================
# 🧭 HÀM TIỆN LỢI: TỰ CHỌN TEMPLATE THEO PREFIX ROUTE
# ==========================================================
def get_template_by_path(path: str) -> Jinja2Templates:
    """
    Trả về template phù hợp theo URL.
    - /admin/...   → templates["admin"]
    - /teacher/... → templates["teacher"]
    - /student/... → templates["student"]
    - /auth/...    → templates["auth"]
    - /            → templates["root"]
    """
    if path.startswith("/admin"):
        return templates["admin"]
    elif path.startswith("/teacher"):
        return templates["teacher"]
    elif path.startswith("/student"):
        return templates["student"]
    elif path.startswith("/auth"):
        return templates["auth"]
    return templates["root"]
