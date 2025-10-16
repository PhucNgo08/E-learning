import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.services.password_service import get_password_hash  # ✅ Bcrypt
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 🧩 CREATE - Thêm người dùng mới
# ============================================================
def create_user(username: str, email: str, password: str, full_name: str, role: str, db: Session):
    """Tạo mới người dùng trong hệ thống"""
    try:
        # Kiểm tra username hoặc email trùng
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Tên đăng nhập đã tồn tại.")
        if db.query(User).filter(User.email == email).first():
            raise ValueError("Email đã tồn tại.")

        # ✅ Hash mật khẩu bằng bcrypt
        hashed_password = get_password_hash(password)

        new_user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role=role
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"✅ Đã tạo người dùng mới: {new_user.username} ({new_user.role})")
        return new_user

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo người dùng: {str(e)}") from e


# ============================================================
# 🔍 READ - Lấy thông tin người dùng
# ============================================================
def get_user_by_id(user_id: str, db: Session):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(email: str, db: Session):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(username: str, db: Session):
    """Lấy user theo username — dùng trong xác thực login"""
    return db.query(User).filter(User.username == username).first()


# ============================================================
# ✏️ UPDATE - Cập nhật người dùng
# ============================================================
def update_user(user_id: str, username: str, email: str, password: str, full_name: str, role: str, db: Session):
    """Cập nhật thông tin người dùng"""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    # Kiểm tra trùng lặp
    if db.query(User).filter(User.username == username, User.id != user_id).first():
        raise ValueError("Tên đăng nhập đã được sử dụng bởi người khác.")
    if db.query(User).filter(User.email == email, User.id != user_id).first():
        raise ValueError("Email đã được sử dụng bởi người khác.")

    # Cập nhật thông tin
    user.username = username
    user.email = email
    user.full_name = full_name
    user.role = role

    # ✅ Nếu có nhập mật khẩu mới → hash lại
    if password.strip():
        user.password_hash = get_password_hash(password)

    try:
        db.commit()
        db.refresh(user)
        logger.info(f"✏️ Cập nhật thông tin user: {user.username}")
        return user
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật người dùng: {str(e)}") from e


# ============================================================
# ❌ DELETE - Xóa người dùng
# ============================================================
def delete_user(user_id: str, db: Session):
    """Xóa người dùng theo ID"""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng để xóa.")
    try:
        db.delete(user)
        db.commit()
        logger.info(f"🗑️ Đã xóa người dùng: {user.username}")
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa người dùng: {str(e)}") from e


# ============================================================
# 📋 GET ALL - Lấy tất cả người dùng
# ============================================================
def get_all_users(db: Session):
    """Lấy toàn bộ danh sách người dùng"""
    return db.query(User).order_by(User.created_at.desc()).all()
