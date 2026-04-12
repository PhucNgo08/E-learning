"""
==========================================================
🔐 app/services/common/password_service.py
Module dùng chung để mã hoá, kiểm tra & đổi mật khẩu
Dùng cho: ADMIN – TEACHER – STUDENT
==========================================================
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

import bcrypt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User

# =====================================================
# ⚙️ Logger & bcrypt context
# =====================================================
logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)

_BCRYPT_HASH_PATTERN = re.compile(r"^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$")


# =====================================================
# 🛠️ HỖ TRỢ: KIỂM TRA HASH BCRYPT CÓ HỢP LỆ KHÔNG
# =====================================================
def is_valid_bcrypt_hash(hashed_password: str | None) -> bool:
    """
    Kiểm tra chuỗi hash có phải bcrypt hợp lệ hay không.

    Ví dụ hash giả cần loại:
    '$2a$10$adminhashed'
    """
    if not hashed_password:
        return False

    if not _BCRYPT_HASH_PATTERN.fullmatch(hashed_password):
        return False

    try:
        bcrypt.checkpw(b"__probe__", hashed_password.encode("utf-8"))
        return True
    except ValueError:
        return False
    except Exception:
        return False


# =====================================================
# 🔑 TẠO HASH MẬT KHẨU
# =====================================================
def get_password_hash(password: str) -> str:
    """Tạo hash cho mật khẩu bằng bcrypt."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"❌ [get_password_hash] Lỗi mã hoá mật khẩu: {e}")
        raise ValueError("Không thể mã hoá mật khẩu.")


def hash_password(password: str) -> str:
    """
    Alias tương thích với code cũ.
    Một số file đang import `hash_password`, nên giữ lại để tránh ImportError.
    """
    return get_password_hash(password)


# =====================================================
# 🔍 KIỂM TRA MẬT KHẨU
# =====================================================
def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """
    Kiểm tra mật khẩu nhập vào có khớp với hash hay không.
    Không làm vỡ hệ thống nếu hash cũ bị lỗi / sai định dạng.
    """
    if not plain_password or not hashed_password:
        return False

    if not is_valid_bcrypt_hash(hashed_password):
        logger.warning("⚠️ [verify_password] password_hash không phải bcrypt hợp lệ.")
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"⚠️ [verify_password] Lỗi khi verify mật khẩu: {e}")
        return False


# =====================================================
# 🔁 ĐỔI MẬT KHẨU
# =====================================================
def change_user_password(
    db: Session,
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> dict:
    """Đổi mật khẩu cho user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "❌ Không tìm thấy người dùng."}

    if not user.password_hash:
        return {"success": False, "message": "⚠️ Tài khoản chưa có mật khẩu hợp lệ."}

    if not is_valid_bcrypt_hash(user.password_hash):
        return {
            "success": False,
            "message": "⚠️ Mật khẩu hiện tại trong hệ thống không hợp lệ. Cần đặt lại mật khẩu.",
        }

    if not verify_password(current_password, user.password_hash):
        return {"success": False, "message": "❌ Mật khẩu hiện tại không đúng."}

    if len(new_password) < 6:
        return {"success": False, "message": "⚠️ Mật khẩu mới phải có ít nhất 6 ký tự."}

    if new_password != confirm_password:
        return {"success": False, "message": "❌ Mật khẩu xác nhận không khớp."}

    if verify_password(new_password, user.password_hash):
        return {"success": False, "message": "⚠️ Mật khẩu mới không được trùng mật khẩu cũ."}

    try:
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        user_role = getattr(user, "resolved_role", None) or getattr(user, "role", None) or "user"
        logger.info(f"✅ [{user_role}] {user.username} đổi mật khẩu thành công.")

        return {"success": True, "message": "✅ Đổi mật khẩu thành công."}
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [change_user_password] Lỗi cập nhật DB: {e}")
        return {"success": False, "message": "❌ Lỗi hệ thống. Không thể đổi mật khẩu."}


# =====================================================
# 🛠️ HỖ TRỢ: TỰ ĐỘNG MÃ HOÁ CÁC MẬT KHẨU CŨ / HASH GIẢ
# =====================================================
def fix_unhashed_passwords(db: Session, default_password_if_empty: str = "123456") -> int:
    """
    Quét tất cả user và sửa những password_hash không hợp lệ.

    Quy ước:
    - Nếu password_hash rỗng / NULL -> đặt mặc định '123456' rồi hash lại
    - Nếu password_hash không phải bcrypt hợp lệ -> coi đó là mật khẩu thô cũ
      và hash lại chính chuỗi đó
    - Nếu password_hash là chuỗi "giả bcrypt" như '$2a$10$adminhashed'
      -> không thể khôi phục mật khẩu gốc, sẽ đặt về '123456'
    """
    users = db.query(User).all()
    fixed = 0

    for u in users:
        current_hash = u.password_hash

        if is_valid_bcrypt_hash(current_hash):
            continue

        if not current_hash:
            new_plain = default_password_if_empty
            reason = "trống"
        else:
            if (
                current_hash.startswith("$2a$")
                or current_hash.startswith("$2b$")
                or current_hash.startswith("$2y$")
            ):
                new_plain = default_password_if_empty
                reason = "hash giả hoặc hỏng"
            else:
                new_plain = current_hash
                reason = "mật khẩu thô cũ"

        try:
            u.password_hash = get_password_hash(new_plain)
            u.updated_at = datetime.utcnow()
            fixed += 1
            logger.info(
                f"🔁 Mã hoá lại mật khẩu cho {u.username} "
                f"(lý do: {reason}, mật khẩu mới dùng để hash: {new_plain})"
            )
        except Exception as e:
            logger.warning(f"⚠️ Không thể mã hoá mật khẩu của {u.username}: {e}")

    if fixed > 0:
        db.commit()
        logger.info(f"🎯 Đã mã hoá lại {fixed} mật khẩu cũ/không hợp lệ.")
    else:
        logger.info("✅ Tất cả tài khoản đều đã dùng bcrypt hợp lệ.")

    return fixed