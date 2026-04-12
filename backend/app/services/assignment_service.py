from datetime import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


# ==========================================================
# 📋 1️⃣ Lấy danh sách bài tập
# ==========================================================
def get_all(db: Session):
    """Admin – Lấy tất cả bài tập"""
    return db.query(Assignment).order_by(Assignment.created_at.desc()).all()


# ==========================================================
# 🔍 2️⃣ Lấy 1 bài tập theo ID
# ==========================================================
def get_by_id(db: Session, assignment_id: str):
    """Tìm bài tập theo ID"""
    return db.query(Assignment).filter(Assignment.id == assignment_id).first()


# ==========================================================
# ➕ 3️⃣ Tạo bài tập mới
# ==========================================================
def create_assignment(
    db: Session,
    title: str,
    course_id: str,
    teacher_id: str,
    description: str | None = None,
    due_date: datetime | None = None,
    module_id: str | None = None,
    submission_type: str = "individual",
    total_points: float = 10,
):
    """Tạo mới một bài tập"""
    title = _clean_text(title)
    description = _clean_text(description)

    if not title:
        raise ValueError("Tiêu đề bài tập không được để trống.")
    if not course_id:
        raise ValueError("course_id không được để trống.")
    if not teacher_id:
        raise ValueError("teacher_id không được để trống.")
    if due_date is None:
        raise ValueError("Hạn nộp không được để trống.")

    now = datetime.utcnow()

    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        course_id=course_id,
        teacher_id=teacher_id,
        module_id=module_id,
        due_date=due_date,
        submission_type=submission_type,
        total_points=total_points,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment
    except SQLAlchemyError:
        db.rollback()
        raise


# ==========================================================
# ✏️ 4️⃣ Cập nhật bài tập
# ==========================================================
def update_assignment(
    db: Session,
    assignment_id: str,
    title: str,
    description: str | None = None,
    due_date: datetime | None = None,
):
    """Cập nhật thông tin bài tập"""
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        return None

    title = _clean_text(title)
    description = _clean_text(description)

    if not title:
        raise ValueError("Tiêu đề bài tập không được để trống.")

    assignment.title = title
    assignment.description = description
    if due_date is not None:
        assignment.due_date = due_date
    assignment.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except SQLAlchemyError:
        db.rollback()
        raise


# ==========================================================
# 🗑️ 5️⃣ Xóa bài tập
# ==========================================================
def delete_assignment(db: Session, assignment_id: str):
    """
    Xóa bài tập và toàn bộ bài nộp / file đính kèm liên quan.
    Lưu ý:
    - Nếu model/schema của bạn dùng cascade DB chuẩn thì có thể chỉ cần db.delete(assignment)
    - Bản này chủ động xóa để tránh lỗi khóa ngoại
    """
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        return False

    try:
        submission_ids = [
            row[0]
            for row in db.query(AssignmentSubmission.id)
            .filter(AssignmentSubmission.assignment_id == assignment_id)
            .all()
        ]

        # Nếu file gắn với submission_id (đúng với schema phổ biến của project)
        if submission_ids and hasattr(AssignmentFile, "submission_id"):
            db.query(AssignmentFile).filter(
                AssignmentFile.submission_id.in_(submission_ids)
            ).delete(synchronize_session=False)

        # Nếu model của bạn thật sự có assignment_id trên AssignmentFile
        elif hasattr(AssignmentFile, "assignment_id"):
            db.query(AssignmentFile).filter(
                AssignmentFile.assignment_id == assignment_id
            ).delete(synchronize_session=False)

        db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id
        ).delete(synchronize_session=False)

        db.delete(assignment)
        db.commit()
        return True

    except SQLAlchemyError:
        db.rollback()
        raise


# ==========================================================
# 📊 6️⃣ Thống kê tổng quan bài tập
# ==========================================================
def get_statistics(db: Session):
    """Thống kê tổng quan bài tập trong hệ thống"""
    total_assignments = db.query(func.count(Assignment.id)).scalar() or 0
    total_submissions = db.query(func.count(AssignmentSubmission.id)).scalar() or 0
    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.status == "graded")
        .scalar()
        or 0
    )

    pending = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.status == "submitted")
        .scalar()
        or 0
    )

    return {
        "total_assignments": int(total_assignments),
        "total_submissions": int(total_submissions),
        "graded": int(graded),
        "pending": int(pending),
    }