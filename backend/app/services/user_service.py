import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.models.security_setting import SecuritySetting
from app.services.common.password_service import get_password_hash  # ✅ bcrypt hash chuẩn

# =====================================================
# 🧩 1️⃣ TẠO NGƯỜI DÙNG
# =====================================================
def create_user(
    username: str,
    email: str,
    password: str,
    full_name: str,
    role: str,
    db: Session,
    academic_year_id: str = None,
    major_id: str = None,
    mssv: str = None
):
    """Tạo mới người dùng (cho phép tạo admin, teacher, student, TA)."""
    try:
        # --- Kiểm tra trùng username/email ---
        if db.query(User).filter(User.username == username).first():
            raise ValueError("❌ Tên đăng nhập đã tồn tại.")
        if db.query(User).filter(User.email == email).first():
            raise ValueError("❌ Email đã tồn tại.")

        # --- Mật khẩu mặc định ---
        if not password or password.strip() == "":
            password = "123456"

        # --- MSSV mặc định nếu là student ---
        if role == "student" and not mssv:
            mssv = username

        # --- Hash mật khẩu ---
        hashed_password = get_password_hash(password)

        # --- Tạo user ---
        new_user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role=role or "student",
            mssv=mssv,
            academic_year_id=academic_year_id or None,
            major_id=major_id or None,
            status="active"
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # --- Tạo SecuritySetting mặc định ---
        db.add(SecuritySetting(user_id=new_user.id))
        db.commit()

        return new_user

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo người dùng: {str(e)}") from e


# =====================================================
# 🔍 2️⃣ HÀM LẤY NGƯỜI DÙNG
# =====================================================
def get_user_by_id(user_id: str, db: Session):
    """Lấy người dùng theo ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(email: str, db: Session):
    """Lấy người dùng theo email (dùng cho đăng nhập hoặc reset password)."""
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


def get_all_users(db: Session):
    """Lấy toàn bộ danh sách người dùng (cho Admin)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    for u in users:
        u.role = u.role or "student"
        u.status = u.status or "active"
    return users


# =====================================================
# ✏️ 3️⃣ CẬP NHẬT NGƯỜI DÙNG
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
    major_id: str = None,
    mssv: str = None
):
    """Cập nhật thông tin người dùng (Admin hoặc Teacher)."""
    user = get_user_by_id(user_id, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng.")

    # --- Kiểm tra trùng username/email ---
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
    user.mssv = mssv or user.mssv

    # --- Nếu có mật khẩu mới ---
    if password and password.strip() != "":
        user.password_hash = get_password_hash(password)

    try:
        db.commit()
        db.refresh(user)
        return user
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật người dùng: {str(e)}") from e


# =====================================================
# 🔐 4️⃣ ĐẶT LẠI MẬT KHẨU (QUÊN MẬT KHẨU)
# =====================================================
def update_password(db: Session, email: str, new_password: str):
    """Đặt lại mật khẩu cho người dùng (dùng trong reset password)."""
    user = get_user_by_email(email, db)
    if not user:
        raise ValueError("Không tìm thấy người dùng với email này.")

    user.password_hash = get_password_hash(new_password)
    try:
        db.commit()
        db.refresh(user)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi đặt lại mật khẩu: {str(e)}") from e


# =====================================================
# 🚫 5️⃣ VÔ HIỆU HÓA TÀI KHOẢN
# =====================================================
def deactivate_user(user_id: str, db: Session):
    """Vô hiệu hóa tài khoản người dùng."""
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
# ♻️ 6️⃣ KHÔI PHỤC TÀI KHOẢN
# =====================================================
def restore_user(user_id: str, db: Session):
    """Khôi phục tài khoản bị vô hiệu hóa."""
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
