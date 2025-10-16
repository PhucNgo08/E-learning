from app.models.user import User
from app.models.major import Major
from sqlalchemy.orm import Session

def get_all_teachers(db: Session):
    """Lấy tất cả giảng viên và trợ giảng"""
    return (
        db.query(User)
        .outerjoin(Major)
        .filter(User.role.in_(["teacher", "assistant"]))
        .all()
    )

def get_teacher(db: Session, teacher_id: str):
    """Lấy 1 giảng viên cụ thể"""
    return db.query(User).filter(User.id == teacher_id).first()

def create_teacher(db: Session, username: str, email: str, full_name: str, role: str):
    """Tạo giảng viên mới"""
    new_teacher = User(username=username, email=email, full_name=full_name, role=role)
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return new_teacher

def update_teacher(db: Session, teacher_id: str, full_name: str, email: str, role: str):
    """Cập nhật thông tin giảng viên"""
    teacher = db.query(User).filter(User.id == teacher_id).first()
    if teacher:
        teacher.full_name = full_name
        teacher.email = email
        teacher.role = role
        db.commit()
        db.refresh(teacher)
    return teacher
