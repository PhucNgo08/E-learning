"""
==========================================================
🔐 app/services/common/password_service.py
Module dùng chung để mã hoá, kiểm tra & đổi mật khẩu
Dùng cho: ADMIN – TEACHER – STUDENT
==========================================================
"""
from passlib.context import CryptContext
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User
import re

# =====================================================
# ⚙️ Logger & bcrypt context
# =====================================================
logger = logging.getLogger(__name__)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# =====================================================
# 🔑 TẠO HASH MẬT KHẨU
# =====================================================
def get_password_hash(password: str) -> str:
    """Tạo hash cho mật khẩu (bcrypt)."""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"❌ [get_password_hash] Lỗi mã hoá mật khẩu: {e}")
        raise ValueError("Không thể mã hoá mật khẩu.")

# =====================================================
# 🔍 KIỂM TRA MẬT KHẨU
# =====================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu nhập vào có khớp với hash không."""
    if not plain_password or not hashed_password:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"⚠️ [verify_password] Hash không hợp lệ hoặc lỗi: {e}")
        return False

# =====================================================
# 🔁 ĐỔI MẬT KHẨU (DÙNG CHUNG CHO ADMIN / TEACHER / STUDENT)
# =====================================================
def change_user_password(
    db: Session,
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> dict:
    """Đổi mật khẩu cho user (admin / teacher / student)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "❌ Không tìm thấy người dùng."}

    if not user.password_hash:
        return {"success": False, "message": "⚠️ Tài khoản chưa có mật khẩu hợp lệ."}

    # --- 1️⃣ Xác minh mật khẩu hiện tại ---
    if not verify_password(current_password, user.password_hash):
        return {"success": False, "message": "❌ Mật khẩu hiện tại không đúng."}

    # --- 2️⃣ Kiểm tra mật khẩu mới ---
    if len(new_password) < 6:
        return {"success": False, "message": "⚠️ Mật khẩu mới phải có ít nhất 6 ký tự."}

    # (Tùy chọn) yêu cầu mật khẩu mạnh hơn
    # if not re.search(r"[A-Z]", new_password) or not re.search(r"\d", new_password):
    #     return {"success": False, "message": "⚠️ Mật khẩu mới cần ít nhất 1 chữ hoa và 1 chữ số."}

    if new_password != confirm_password:
        return {"success": False, "message": "❌ Mật khẩu xác nhận không khớp."}

    if verify_password(new_password, user.password_hash):
        return {"success": False, "message": "⚠️ Mật khẩu mới không được trùng mật khẩu cũ."}

    # --- 3️⃣ Cập nhật vào DB ---
    try:
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        logger.info(f"✅ [{user.role}] {user.username} đổi mật khẩu thành công.")
        return {"success": True, "message": "✅ Đổi mật khẩu thành công."}
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [change_user_password] Lỗi cập nhật DB: {e}")
        return {"success": False, "message": "❌ Lỗi hệ thống. Không thể đổi mật khẩu."}

# =====================================================
# 🛠️ HỖ TRỢ: TỰ ĐỘNG MÃ HOÁ CÁC MẬT KHẨU CŨ (chưa bcrypt)
# =====================================================
def fix_unhashed_passwords(db: Session) -> int:
    """
    Tự động quét & mã hoá lại tất cả mật khẩu chưa được mã hoá.
    Nếu trống → đặt mặc định là '123456' và mã hoá bằng bcrypt.
    """
    users = db.query(User).all()
    fixed = 0
    for u in users:
        if not u.password_hash or not (u.password_hash.startswith("$2b$") or u.password_hash.startswith("$2a$")):
            old_pw = u.password_hash or "123456"
            try:
                u.password_hash = get_password_hash(old_pw)
                fixed += 1
                logger.info(f"🔁 Mã hoá lại mật khẩu cho {u.username}: {old_pw} → bcrypt")
            except Exception as e:
                logger.warning(f"⚠️ Không thể mã hoá mật khẩu của {u.username}: {e}")

    if fixed > 0:
        db.commit()
        logger.info(f"🎯 Đã mã hoá lại {fixed} mật khẩu cũ.")
    else:
        logger.info("✅ Tất cả tài khoản đều đã được mã hoá bcrypt.")

    return fixed
