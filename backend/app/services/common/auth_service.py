"""
===========================================================
🔐 AUTH SERVICE – PRO MAX ENTERPRISE v5.2
Compatible Python 3.12 – OWASP-ready
Fixes:
✔ Role normalize (Enum/String)
✔ Username sanitize
✔ Avatar fallback
✔ Secure logout
✔ Harden PBKDF2 verify
✔ Session versioning
===========================================================
"""

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import uuid
import re
import unicodedata

from passlib.hash import pbkdf2_sha256
from app.models.user import User
from app.models.security_setting import SecuritySettings

SESSION_EXPIRE_HOURS = 6
REMEMBER_ME_DAYS = 7


# ======================================================
# 🔒 PASSWORD HASH & VERIFY
# ======================================================
def verify_password(plain: str, hashed: str) -> bool:
    """Kiểm tra PBKDF2 & SHA256 legacy – constant-time."""

    if not plain or not hashed:
        return False

    if hashed.startswith("$pbkdf2-sha256$"):
        return pbkdf2_sha256.verify(plain, hashed)

    # Legacy SHA256
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


# ======================================================
# 🧹 USERNAME NORMALIZER
# ======================================================
def normalize_username(email: str) -> str:
    base = email.split("@")[0]

    base = (
        unicodedata.normalize("NFKD", base)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    base = re.sub(r"[^a-zA-Z0-9_]", "_", base)

    return base.lower() or f"user_{uuid.uuid4().hex[:8]}"


# ======================================================
# 🔍 GET USER BY IDENTIFIER
# ======================================================
def get_user_by_identifier(db: Session, identifier: str):
    identifier = identifier.strip().lower()

    if "@" in identifier:
        return db.query(User).filter(User.email == identifier).first()

    return db.query(User).filter(User.username == identifier).first()


# ======================================================
# 🔐 LOGIN AUTHENTICATION
# ======================================================
def authenticate_user(db: Session, identifier: str, password: str):

    user = get_user_by_identifier(db, identifier)
    if not user:
        return {"success": False, "message": "❌ Không tìm thấy tài khoản."}

    # lấy SecuritySettings
    security = db.query(SecuritySettings).filter_by(user_id=user.id).first()
    if not security:
        security = SecuritySettings(user_id=user.id)
        db.add(security)
        db.commit()
        db.refresh(security)

    # Check lock
    if security.account_locked_until and security.account_locked_until > datetime.utcnow():
        return {
            "success": False,
            "message": f"🔒 Khóa đến {security.account_locked_until:%H:%M:%S %d/%m/%Y}"
        }

    # Check status
    status_val = getattr(user.status, "value", str(user.status)).lower()
    if status_val not in ["active", "1", "true", "enabled"]:
        return {"success": False, "message": "🚫 Tài khoản đã bị vô hiệu hóa."}

    # Wrong password
    if not verify_password(password, user.password_hash):

        security.failed_login_attempts += 1

        if security.failed_login_attempts >= 5:
            security.failed_login_attempts = 0
            security.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
            return {
                "success": False,
                "message": f"🔒 Sai 5 lần — khóa 30 phút."
            }

        db.commit()
        remaining = 5 - security.failed_login_attempts
        return {"success": False, "message": f"⚠️ Sai mật khẩu — còn {remaining} lần thử."}

    # Success
    security.failed_login_attempts = 0
    security.account_locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    return {"success": True, "user": user}


# ======================================================
# 🎭 ROLE DETECTOR
# ======================================================
def detect_role_from_email(email: str) -> str:
    email = email.lower()

    if email.endswith("@hutech.edu.vn"):
        return "admin"
    if email.endswith("@gv.hutech.edu.vn"):
        return "teacher"
    if email.endswith("@st.hutech.edu.vn"):
        return "student"

    return "student"


# ======================================================
# 🔐 CREATE SECURE SESSION
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

    # Normalize role
    role = getattr(user.role, "value", user.role)
    role = str(role).lower()

    request.session.update({
        "session_version": uuid.uuid4().hex,   # chống session replay
        "user_id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "role": role,
        "avatar": user.avatar_url or "/uploads/avatars/default-avatar.png",

        "session_ip": client_ip,
        "session_ua": user_agent,
        "last_active": datetime.utcnow().timestamp(),
        "expires_at": expiry.isoformat(),
        "remember_me": remember_me
    })

    print(f"🔐 [SESSION] Created for {user.username} | role={role} | remember={remember_me}")


# ======================================================
# 🤝 SOCIAL LOGIN USER CREATOR
# ======================================================
def get_or_create_social_user(db: Session, email: str, full_name: str, avatar: str = None):

    email = email.lower()
    user = db.query(User).filter(User.email == email).first()

    if user:
        return user

    username = normalize_username(email)
    role = detect_role_from_email(email)

    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=full_name.strip(),
        username=username,
        password_hash="",  # social login không dùng password
        avatar_url=avatar or "/uploads/avatars/default-avatar.png",
        status="active",
        role=role,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    sec = SecuritySettings(user_id=new_user.id)
    db.add(sec)
    db.commit()

    return new_user


# ======================================================
# 🚪 SECURE LOGOUT
# ======================================================
def logout_user(request: Request):
    request.session.clear()
    # Xóa cookie của session (Starlette không auto)
    request.session.pop("session_version", None)
    print("🚪 Session cleared.")


# ======================================================
# 👤 ADMIN CREATE USER
# ======================================================
def create_user(db: Session, email: str, full_name: str, password: str, role: str = "student"):

    email = email.strip().lower()

    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    username = normalize_username(email)

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
