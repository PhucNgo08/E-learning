from sqlalchemy.orm import Session
from app.models.classes import Class
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.course import Course

def get_teacher_classes(db: Session):
    """Lấy danh sách lớp do giáo viên phụ trách"""
    return db.query(Class).filter(Class.status.in_(["active", "open_for_enrollment"])).all()

def get_class_info(db: Session, class_id: str):
    """Thông tin chi tiết của lớp"""
    return db.query(Class).filter(Class.id == class_id).first()

def get_students_in_class(db: Session, class_id: str):
    """Danh sách học viên trong lớp"""
    return (
        db.query(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.class_id == class_id, User.role == "student")
        .all()
    )
