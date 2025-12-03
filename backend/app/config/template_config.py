from pathlib import Path
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import os


# ==========================================================
# 📌 1) ĐỊNH NGHĨA BASE_DIR CHÍNH XÁC 100%
# ==========================================================
# File này nằm tại:
# backend/app/config/template_config.py
# Project root cần là:
# KHoaHocOnline/ (nằm trên backend)

BASE_DIR = Path(__file__).resolve().parents[3]   # LÊN 3 CẤP: config → app → backend → KHoaHocOnline


# ==========================================================
# 📌 2) ĐƯỜNG DẪN ĐẾN TEMPLATE ROOT
# ==========================================================
ROOT_TEMPLATE_DIR = BASE_DIR / "frontend" / "react-app" / "layouts" / "templates"


# ==========================================================
# 📌 3) LOG KIỂM TRA – chỉ chạy 1 lần
# ==========================================================
def log_template_config():
    print("=" * 80)
    print("📁 [TEMPLATE CONFIG] Root template dir:", ROOT_TEMPLATE_DIR)
    print("📂 Exists:", ROOT_TEMPLATE_DIR.exists())
    print("📂 Test student/discussion/reply_block.html:",
          (ROOT_TEMPLATE_DIR / "student" / "discussion" / "reply_block.html").exists())
    print("=" * 80)


if not os.environ.get("TEMPLATE_LOGGED"):
    os.environ["TEMPLATE_LOGGED"] = "1"
    log_template_config()


# ==========================================================
# 📌 4) KHỞI TẠO TEMPLATE ENGINE (Admin / Teacher / Student / Auth / Root)
# ==========================================================
templates = {
    "admin": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "admin")),
    "teacher": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "teacher")),
    "student": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "student")),
    "auth": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR / "auth")),
    "root": Jinja2Templates(directory=str(ROOT_TEMPLATE_DIR)),
}


# ==========================================================
# 📌 5) GLOBAL VARIABLES DÙNG CHO MỌI TEMPLATE
# ==========================================================
for name, tpl in templates.items():
    tpl.env.globals.update({
        "now": lambda: datetime.utcnow() + timedelta(hours=7),
        "year": (datetime.utcnow() + timedelta(hours=7)).year,
        "app_name": f"E-Learning Platform ({name.capitalize()})",
        "version": "1.0.0",
        "company": "Online Education Team",
        "base_url": "/",
    })


# ==========================================================
# 📌 6) FILTER CHUNG: filesize, datetime, date_short
# ==========================================================
def filesize_fmt(value: int):
    if not value:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def datetime_fmt(value: datetime):
    if not value:
        return ""
    return (value + timedelta(hours=7)).strftime("%H:%M - %d/%m/%Y")


def date_short(value: datetime):
    if not value:
        return ""
    return (value + timedelta(hours=7)).strftime("%d/%m/%Y")


# Đăng ký filter
for tpl in templates.values():
    tpl.env.filters["filesize"] = filesize_fmt
    tpl.env.filters["datetime"] = datetime_fmt
    tpl.env.filters["date_short"] = date_short


# ==========================================================
# 📌 7) FILTER todatetime (parse ISO string → datetime)
# ==========================================================
def todatetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except Exception:
        return value


for tpl in templates.values():
    tpl.env.filters["todatetime"] = todatetime


# ==========================================================
# 📌 8) HÀM TIỆN LỢI CHỌN TEMPLATE THEO PREFIX
# ==========================================================
def get_template_by_path(path: str) -> Jinja2Templates:
    if path.startswith("/admin"):
        return templates["admin"]
    if path.startswith("/teacher"):
        return templates["teacher"]
    if path.startswith("/student"):
        return templates["student"]
    if path.startswith("/auth"):
        return templates["auth"]
    return templates["root"]

# ==========================================================
# 🕓 FILTER BỔ SUNG: todatetime — chuyển chuỗi ISO thành datetime
# ==========================================================
from datetime import datetime

def todatetime(value):
    """Chuyển chuỗi ISO 8601 (yyyy-MM-ddTHH:mm:ss) thành datetime object."""
    if not value:
        return None
    try:
        # Nếu có ký tự 'Z' (ISO format UTC), loại bỏ trước khi parse
        return datetime.fromisoformat(value.replace("Z", ""))
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return value

# 🔗 Đăng ký filter cho tất cả template
for tpl in templates.values():
    tpl.env.filters["todatetime"] = todatetime
# ==========================================================
# 📌 9) GLOBAL CONTEXT CHO STUDENT — LẤY SỐ DƯ VÍ
# ==========================================================
from starlette.requests import Request
from app.services.wallet_service import get_balance
from app.database.connection import get_db

def student_globals(request: Request):
    """
    Hàm global cho toàn bộ layout_student.html
    → Tự động lấy avatar + số dư ví + thông tin realtime.
    """
    try:
        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if role == "student" and user_id:
            db = next(get_db())

            # import ở đây để tránh lỗi vòng import
            from app.models.user import User
            from app.services.wallet_service import get_balance

            user = db.query(User).filter(User.id == user_id).first()

            # Ưu tiên avatar theo thứ tự:
            # 1. session (sau khi upload hình)
            # 2. avatar_url trong DB
            # 3. avatar mặc định
            avatar = (
                request.session.get("user_avatar")
                or (user.avatar_url if user and user.avatar_url else None)
                or "/uploads/avatars/default-avatar.png"
            )

            balance = get_balance(db, user_id)

            return {
                "wallet_balance": balance,
                "avatar_url": avatar
            }

        # Nếu không phải student
        return {
            "wallet_balance": 0,
            "avatar_url": "/uploads/avatars/default-avatar.png"
        }

    except:
        return {
            "wallet_balance": 0,
            "avatar_url": "/uploads/avatars/default-avatar.png"
        }



# Gắn vào ENV của template student
templates["student"].env.globals.update({
    "student_globals": student_globals
})
