import hashlib
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.models.security_setting import SecuritySetting


# =====================================================
# 🔒 Mã hóa mật khẩu
# =====================================================
def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng SHA256"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# =====================================================
# ➕ Tạo người dùng
# =====================================================
def create_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    db: Session,
    academic_year_id: str = None,
    major_id: str = None
):
    """Tạo mới người dùng (cho phép tạo admin, teacher, student, TA)"""
    try:
        # Kiểm tra trùng username/email
        if db.query(User).filter(User.username == username).first():
            raise ValueError("Tên đăng nhập đã tồn tại.")
        if db.query(User).filter(User.email == email).first():
            raise ValueError("Email đã tồn tại.")

        new_user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role or "student",
            academic_year_id=academic_year_id or None,
            major_id=major_id or None,
            status="active"
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Tạo security mặc định
        db.add(SecuritySetting(user_id=new_user.id))
        db.commit()
        return new_user

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo người dùng: {str(e)}") from e


# =====================================================
# 🔍 Lấy người dùng
# =====================================================
def get_user_by_id(user_id: str, db: Session):
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db: Session):
    """Lấy danh sách người dùng, đảm bảo có role/status"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    for u in users:
        u.role = u.role or "student"
        u.status = u.status or "active"
    return users


# =====================================================
# ✏️ Cập nhật người dùng
# =====================================================
def update_user(
    user_id: str,
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    db: Session,
    academic_year_id: str = None,
    major_id: str = None
):
    """Cập nhật thông tin người dùng"""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    if db.query(User).filter(User.username == username, User.id != user_id).first():
        raise ValueError("Tên đăng nhập đã được sử dụng.")
    if db.query(User).filter(User.email == email, User.id != user_id).first():
        raise ValueError("Email đã được sử dụng.")

    user.username = username
    user.email = email
    user.full_name = full_name
    user.role = role
    user.academic_year_id = academic_year_id or None
    user.major_id = major_id or None

    if password.strip():
        user.password_hash = hash_password(password)

    try:
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật người dùng: {str(e)}") from e


# =====================================================
# 🚫 Vô hiệu hóa tài khoản
# =====================================================
def deactivate_user(user_id: str, db: Session):
    """Vô hiệu hóa tài khoản"""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng.")
    if user.status == "inactive":
        raise ValueError("Tài khoản đã bị vô hiệu hóa.")

    user.status = "inactive"
    try:
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi vô hiệu hóa tài khoản: {str(e)}") from e


# =====================================================
# 🔄 Khôi phục tài khoản
# =====================================================
def restore_user(user_id: str, db: Session):
    """Khôi phục tài khoản"""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng.")
    if user.status == "active":
        raise ValueError("Tài khoản đang hoạt động.")

    user.status = "active"
    try:
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi khôi phục tài khoản: {str(e)}") from e
