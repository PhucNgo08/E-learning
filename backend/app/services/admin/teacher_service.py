import uuid
import os
import shutil
from passlib.hash import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.major import Major

# 🎯 Role hợp lệ theo ENUM users.role
VALID_ROLES = ["teacher", "teaching_assistant"]

# Thư mục upload avatar
AVATAR_DIR = "app/static/uploads/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)


# ================================================================
# 📌 1. Danh sách & chi tiết giáo viên
# ================================================================
def get_all_teachers(db: Session):
    """Lấy toàn bộ giảng viên và trợ giảng"""
    return (
        db.query(User)
        .outerjoin(Major)
        .filter(User.role.in_(VALID_ROLES))
        .all()
    )


def get_teacher(db: Session, teacher_id: str):
    return db.query(User).filter(User.id == teacher_id).first()


# ================================================================
# 📌 2. Tạo tài khoản giáo viên
# ================================================================
def create_teacher(db: Session, username: str, email: str, full_name: str, role: str):
    if role not in VALID_ROLES:
        role = "teacher"

    # 👇 Tạo password mặc định
    default_password = "123456"
    password_hash = bcrypt.hash(default_password)

    new_teacher = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        full_name=full_name,
        role=role,
        password_hash=password_hash
    )

    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return new_teacher


# ================================================================
# 📌 3. Cập nhật thông tin giáo viên
# ================================================================
def update_teacher(db: Session, teacher_id: str, full_name: str, email: str, role: str):
    if role not in VALID_ROLES:
        role = "teacher"

    teacher = db.query(User).filter(User.id == teacher_id).first()

    if teacher:
        teacher.full_name = full_name
        teacher.email = email
        teacher.role = role
        db.commit()
        db.refresh(teacher)

    return teacher


# ================================================================
# 📌 4. Upload Avatar cho giáo viên
# ================================================================
def update_teacher_avatar(db: Session, teacher_id: str, file):
    """
    Upload avatar:
    - Lưu vào /app/static/uploads/avatars
    - Update users.avatar_url = '/static/uploads/avatars/...'
    """

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        return None

    # Tạo tên file
    ext = os.path.splitext(file.filename)[1]
    filename = f"{teacher_id}{ext}"
    avatar_path = os.path.join(AVATAR_DIR, filename)

    # Lưu file
    with open(avatar_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # URL để Jinja render
    teacher.avatar_url = f"/static/uploads/avatars/{filename}"

    db.commit()
    db.refresh(teacher)

    return teacher


# ================================================================
# 📌 5. Reset Password
# ================================================================
def reset_teacher_password(db: Session, teacher_id: str):
    """
    Reset mật khẩu cho giáo viên:
    - Sinh mật khẩu mới ngẫu nhiên
    - Hash bằng bcrypt
    """

    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        return None, None

    # 🔐 Sinh mật khẩu mới (8 ký tự)
    new_password = uuid.uuid4().hex[:8]

    teacher.password_hash = bcrypt.hash(new_password)
    db.commit()
    db.refresh(teacher)

    # Trả về mật khẩu plain để hiển thị cho admin
    return teacher, new_password
