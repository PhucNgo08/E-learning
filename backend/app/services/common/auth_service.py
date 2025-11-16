"""
==========================================================
🔐 AUTH SERVICE (PRO MAX ENTERPRISE v5.1 - FIXED FOR PYTHON 3.12)
- Dùng PBKDF2-SHA256 thay cho bcrypt (không lỗi, bảo mật cao)
- Vẫn hỗ trợ SHA256 legacy
==========================================================
"""

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import uuid

from passlib.hash import pbkdf2_sha256   # 🔥 Thay cho bcrypt

from app.models.user import User
from app.models.security_setting import SecuritySettings


SESSION_EXPIRE_HOURS = 6
REMEMBER_ME_DAYS = 7


# ======================================================
# 🔐 HASH & VERIFY (PBKDF2 + SHA256 LEGACY)
# ======================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu PBKDF2 hoặc SHA256."""

    if not plain_password or not hashed_password:
        return False

    # PBKDF2 mới
    if hashed_password.startswith("$pbkdf2-sha256$"):
        return pbkdf2_sha256.verify(plain_password, hashed_password)

    # SHA256 cũ
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


def hash_password(password: str) -> str:
    """Hash mật khẩu bằng PBKDF2-SHA256 (OWASP recommended)."""
    return pbkdf2_sha256.hash(password)


# ======================================================
# 🔍 GET USER BY IDENTIFIER
# ======================================================
def get_user_by_identifier(db: Session, identifier: str):
    identifier = identifier.strip().lower()

    if "@" in identifier:
        return db.query(User).filter(User.email == identifier).first()

    return db.query(User).filter(User.username == identifier).first()


# ======================================================
# 🔐 LOGIN
# ======================================================
def authenticate_user(db: Session, identifier: str, password: str):

    user = get_user_by_identifier(db, identifier)
    if not user:
        return {"success": False, "message": "❌ Không tìm thấy tài khoản."}

    security = db.query(SecuritySettings).filter_by(user_id=user.id).first()
    if not security:
        security = SecuritySettings(user_id=user.id)
        db.add(security)
        db.commit()

    # Bị khóa tạm thời
    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        return {
            "success": False,
            "message": f"🔒 Tài khoản bị khóa đến {security.account_locked_until:%H:%M:%S %d/%m/%Y}"
        }

    # User chưa active
    status_val = getattr(user.status, "value", str(user.status)).lower()
    if status_val not in ["active", "1", "true", "enabled"]:
        return {"success": False, "message": "🚫 Tài khoản đã bị vô hiệu hóa."}

    # Sai mật khẩu
    if not verify_password(password, user.password_hash):
        security.failed_login_attempts += 1

        if security.failed_login_attempts >= 5:
            security.failed_login_attempts = 0
            security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
            return {
                "success": False,
                "message": f"🔒 Sai 5 lần — khóa đến {security.account_locked_until:%H:%M:%S %d/%m/%Y}"
            }

        db.commit()
        return {
            "success": False,
            "message": f"⚠️ Sai mật khẩu ({5 - security.failed_login_attempts} lần thử còn lại)."
        }

    # Thành công
    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    return {"success": True, "user": user}


# ======================================================
# 🔐 AUTO MAP ROLE
# ======================================================
def detect_role_from_email(email: str) -> str:
    email = email.lower()

    if email.endswith("@hutech.edu.vn"): return "admin"
    if email.endswith("@gv.hutech.edu.vn"): return "teacher"
    if email.endswith("@st.hutech.edu.vn"): return "student"

    return "student"


# ======================================================
# 💾 CREATE SESSION
# ======================================================
def create_user_session(request: Request, user: User, remember_me: bool = False):

    request.session.clear()

    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "Unknown-UA")

    expiry = (
        datetime.utcnow() + timedelta(days=REMEMBER_ME_DAYS)
        if remember_me else
        datetime.utcnow() + timedelta(hours=SESSION_EXPIRE_HOURS)
    )

    request.session.update({
        "user_id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": getattr(user.role, "value", user.role),
        "avatar": user.avatar_url or "/uploads/avatars/default-avatar.png",

        "last_active": datetime.utcnow().timestamp(),
        "session_ip": client_ip,
        "session_ua": user_agent,
        "expires_at": expiry.isoformat()
    })

    print(f"🔐 Session created for {user.username} | Remember = {remember_me}")


# ======================================================
# 🔀 SOCIAL USER CREATOR
# ======================================================
def get_or_create_social_user(db: Session, email: str, full_name: str, avatar: str = None):

    email = email.lower()
    user = db.query(User).filter(User.email == email).first()

    if user:
        return user

    username = email.split("@")[0]
    role = detect_role_from_email(email)

    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name,
        username=username,
        password_hash="",  
        avatar_url=avatar or "/uploads/avatars/default-avatar.png",
        status="active",
        role=role,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    db.add(SecuritySettings(user_id=new_user.id))
    db.commit()

    return new_user


# ======================================================
# 🚪 LOGOUT
# ======================================================
def logout_user(request: Request):
    request.session.clear()
    print("🚪 Session cleared.")


# ======================================================
# 👤 ADMIN CREATE USER
# ======================================================
def create_user(db: Session, email: str, full_name: str, password: str, role: str = "student"):

    email = email.strip().lower()

    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    username = email.split("@")[0]

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name.strip(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        status="active",
        avatar_url="/uploads/avatars/default-avatar.png",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(SecuritySettings(user_id=user.id))
    db.commit()

    return user
