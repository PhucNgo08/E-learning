"""
==========================================================
🔐 app/services/common/auth_service.py
Dịch vụ xử lý xác thực (đăng nhập / đăng xuất / kiểm tra vai trò)
==========================================================
"""
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import bcrypt
import uuid

from app.models.user import User
from app.models.security_setting import SecuritySettings
from app.config.paths import UPLOAD_AVATARS
from app.config.template_config import templates

# =====================================================
# ⚙️ THIẾT LẬP CHUNG
# =====================================================
SESSION_EXPIRE_HOURS = 6
templates = templates["auth"]

# =====================================================
# 🧠 HÀM HỖ TRỢ XỬ LÝ BCRYPT
# =====================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu người dùng nhập vào có khớp với hash không"""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Tạo hash cho mật khẩu (bcrypt)"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# =====================================================
# 🔐 XÁC THỰC NGƯỜI DÙNG (EMAIL + PASSWORD)
# =====================================================
def authenticate_user(db: Session, email: str, password: str):
    """
    Xác thực người dùng dựa trên email và mật khẩu.
    Bao gồm kiểm tra khóa tạm thời và vô hiệu hóa.
    """
    user = db.query(User).filter(User.email == email.strip().lower()).first()

    if not user:
        return {"success": False, "message": "❌ Không tìm thấy tài khoản."}

    # Lấy hoặc tạo bản ghi SecuritySettings
    security = db.query(SecuritySettings).filter(SecuritySettings.user_id == user.id).first()
    if not security:
        security = SecuritySettings(user_id=user.id)
        db.add(security)
        db.commit()
        db.refresh(security)

    # 🔒 Nếu tài khoản đang bị khóa tạm thời
    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
        return {
            "success": False,
            "message": f"🔒 Tài khoản đang bị khóa tạm thời đến {lock_time}."
        }

    # 🚫 Nếu tài khoản bị vô hiệu hóa
    if str(user.status) != "active":
        return {
            "success": False,
            "message": "🚫 Tài khoản của bạn đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên."
        }

    # ✅ Kiểm tra mật khẩu
    if not verify_password(password, user.password_hash):
        security.failed_login_attempts += 1

        # Nếu nhập sai >= 5 lần → khóa 30 phút
        if security.failed_login_attempts >= 5:
            security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            security.failed_login_attempts = 0
            db.commit()
            lock_time = security.account_locked_until.strftime("%H:%M:%S %d/%m/%Y")
            return {
                "success": False,
                "message": f"🔒 Sai mật khẩu quá 5 lần — tài khoản bị khóa đến {lock_time}."
            }

        db.commit()
        remaining = 5 - security.failed_login_attempts
        return {
            "success": False,
            "message": f"⚠️ Mật khẩu không đúng. Bạn còn {remaining} lần thử trước khi bị khóa."
        }

    # ✅ Đăng nhập thành công
    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    return {"success": True, "user": user}


# =====================================================
# 💾 LƯU SESSION SAU KHI ĐĂNG NHẬP
# =====================================================
def create_user_session(request: Request, user: User):
    """Lưu thông tin user vào session"""
    request.session.clear()
    request.session.update({
        "user_id": str(user.id),
        "user_full_name": user.full_name,
        "user_email": user.email,
        "role": getattr(user.role, "value", "student"),
        "user_avatar": user.avatar_url or "/uploads/avatars/default-avatar.png",
        "session_start": datetime.utcnow().isoformat(),
    })
    print(f"✅ Session tạo cho {user.full_name} ({user.email})")


# =====================================================
# 🚪 ĐĂNG XUẤT
# =====================================================
def logout_user(request: Request):
    """Xóa session đăng nhập"""
    request.session.clear()
    print("🚪 Session đã được xóa thành công.")


# =====================================================
# 🔍 KIỂM TRA QUYỀN TRUY CẬP
# =====================================================
def require_role(role: str):
    """Decorator kiểm tra quyền truy cập (admin / teacher / student)"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            session_role = request.session.get("role")
            if session_role != role:
                print(f"🚫 Quyền hạn không hợp lệ: yêu cầu={role}, hiện tại={session_role}")
                return RedirectResponse(url="/auth/login", status_code=303)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# =====================================================
# 🧭 TỰ ĐỘNG CHUYỂN HƯỚNG SAU KHI LOGIN
# =====================================================
def get_redirect_by_role(role_name: str) -> str:
    """Xác định đường dẫn điều hướng sau khi đăng nhập"""
    if role_name == "admin":
        return "/admin/dashboard"
    elif role_name == "teacher":
        return "/teacher/dashboard"
    elif role_name == "student":
        return "/student/dashboard"
    return "/auth/login"


# =====================================================
# ⚡ KHỞI TẠO USER MỚI (ĐĂNG KÝ / TẠO BỞI ADMIN)
# =====================================================
def create_user(db: Session, email: str, full_name: str, password: str, role_name: str = "student"):
    """Tạo người dùng mới"""
    # Kiểm tra trùng email
    if db.query(User).filter(User.email == email.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    user = User(
        id=str(uuid.uuid4()),
        full_name=full_name.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        avatar_url="/uploads/avatars/default-avatar.png",
        status="active",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Tạo SecuritySettings mặc định
    db.add(SecuritySettings(user_id=user.id))
    db.commit()

    print(f"👤 Tạo người dùng mới: {user.full_name} ({role_name})")
    return user
