from pathlib import Path
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from starlette.requests import Request
import os

from app.database.connection import get_db


# ==========================================================
# 📌 1) ĐỊNH NGHĨA BASE_DIR CHÍNH XÁC
# ==========================================================
# File này nằm tại:
# backend/app/config/template_config.py
# Project root:
# KHoaHocOnline/
BASE_DIR = Path(__file__).resolve().parents[3]


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
    print(
        "📂 Test student/discussion/reply_block.html:",
        (ROOT_TEMPLATE_DIR / "student" / "discussion" / "reply_block.html").exists()
    )
    print("=" * 80)


if not os.environ.get("TEMPLATE_LOGGED"):
    os.environ["TEMPLATE_LOGGED"] = "1"
    log_template_config()


# ==========================================================
# 📌 4) KHỞI TẠO TEMPLATE ENGINE
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
# 📌 6) FILTER CHUNG
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


def todatetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        try:
            return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return value



def vi_status_label(value):
    if value is None:
        return "Không rõ"
    key = str(value).strip().lower()
    labels = {
        "active": "Đang hoạt động",
        "inactive": "Không hoạt động",
        "suspended": "Tạm khóa",
        "pending": "Đang chờ",
        "pending_approval": "Chờ duyệt",
        "approved": "Đã duyệt",
        "rejected": "Đã từ chối",
        "cancelled": "Đã hủy",
        "completed": "Đã hoàn thành",
        "in_progress": "Đang thực hiện",
        "not_started": "Chưa bắt đầu",
        "submitted": "Đã nộp",
        "graded": "Đã chấm",
        "late": "Nộp muộn",
        "resubmitted": "Đã nộp lại",
        "published": "Đã đăng",
        "draft": "Bản nháp",
        "archived": "Đã lưu trữ",
        "planning": "Đang lên kế hoạch",
        "open_for_enrollment": "Mở ghi danh",
        "paid": "Đã thanh toán",
        "failed": "Thất bại",
        "success": "Thành công",
        "verified": "Đã xác minh",
        "issued": "Đã cấp",
        "manual": "Thủ công",
        "purchase": "Mua khóa học",
        "auto": "Tự động",
        "approval": "Cần duyệt",
        "individual": "Cá nhân",
        "group": "Nhóm",
        "mandatory": "Bắt buộc",
        "elective": "Tự chọn",
        "beginner": "Cơ bản",
        "intermediate": "Trung cấp",
        "advanced": "Nâng cao",
        "easy": "Dễ",
        "medium": "Trung bình",
        "hard": "Khó",
        "practice": "Luyện tập",
        "graded_quiz": "Tính điểm",
        "video": "Video",
        "document": "Tài liệu",
        "quiz": "Bài kiểm tra",
        "assignment": "Bài tập",
        "mixed": "Tổng hợp",
    }
    return labels.get(key, str(value).strip().replace("_", " ") or "Không rõ")


def vi_role_label(value):
    if value is None:
        return "Không rõ"
    key = str(value).strip().lower()
    labels = {
        "admin": "Quản trị viên",
        "teacher": "Giảng viên",
        "student": "Sinh viên",
        "teaching_assistant": "Trợ giảng",
        "prospective_student": "Học viên tiềm năng",
    }
    return labels.get(key, str(value).strip().replace("_", " ") or "Không rõ")


for tpl in templates.values():
    tpl.env.filters["filesize"] = filesize_fmt
    tpl.env.filters["datetime"] = datetime_fmt
    tpl.env.filters["date_short"] = date_short
    tpl.env.filters["todatetime"] = todatetime
    tpl.env.filters["vi_status"] = vi_status_label
    tpl.env.filters["vi_role"] = vi_role_label
    tpl.env.globals["vi_status"] = vi_status_label
    tpl.env.globals["vi_role"] = vi_role_label


# ==========================================================
# 📌 7) HÀM CHỌN TEMPLATE THEO PREFIX
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
# 📌 8) GLOBAL CONTEXT CHO STUDENT — CACHE THEO REQUEST
# ==========================================================
def student_globals(request: Request):
    cached = getattr(request.state, "_student_globals_cache", None)
    if cached is not None:
        return cached

    result = {
        "wallet_balance": 0,
        "avatar_url": "/uploads/avatars/default-avatar.png",
    }

    db = None
    try:
        user_id = request.session.get("user_id")
        role = request.session.get("role")

        if role != "student" or not user_id:
            request.state._student_globals_cache = result
            return result

        avatar = (
            getattr(request.state, "user_avatar", None)
            or request.session.get("user_avatar")
            or "/uploads/avatars/default-avatar.png"
        )

        if hasattr(request.state, "wallet_balance"):
            balance = request.state.wallet_balance
        else:
            db = next(get_db())
            from app.services.wallet_service import get_balance
            balance = get_balance(db, user_id)

        result = {
            "wallet_balance": balance or 0,
            "avatar_url": avatar,
        }

    except Exception:
        result = {
            "wallet_balance": 0,
            "avatar_url": "/uploads/avatars/default-avatar.png",
        }
    finally:
        if db is not None:
            db.close()

    request.state._student_globals_cache = result
    return result


templates["student"].env.globals.update({
    "student_globals": student_globals
})