from passlib.context import CryptContext
import logging

# ==============================
# 🔐 Cấu hình logger & bcrypt context
# ==============================
logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # độ bảo mật cao hơn mặc định (12 > 10)
)

# ==============================
# 🔑 Hash mật khẩu
# ==============================
def get_password_hash(password: str) -> str:
    """
    ✅ Tạo hash cho mật khẩu (sử dụng bcrypt).
    """
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"❌ [get_password_hash] Lỗi khi tạo hash: {e}")
        raise ValueError("Không thể mã hoá mật khẩu.")

# ==============================
# 🔍 Xác thực mật khẩu
# ==============================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    ✅ Kiểm tra mật khẩu người dùng có trùng với hash không.
    Trả về True nếu đúng, False nếu sai hoặc có lỗi.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"⚠️ [verify_password] Lỗi khi so khớp mật khẩu: {e}")
        return False
