from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import uuid

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile


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
    description: str,
    course_id: str,
    due_date: datetime = None,
):
    """Tạo mới một bài tập"""
    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        course_id=course_id,
        due_date=due_date,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)
    return new_assignment


# ==========================================================
# ✏️ 4️⃣ Cập nhật bài tập
# ==========================================================
def update_assignment(
    db: Session,
    assignment_id: str,
    title: str,
    description: str = None,
):
    """Cập nhật thông tin bài tập"""
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        return None

    assignment.title = title
    assignment.description = description
    assignment.updated_at = datetime.now()

    db.commit()
    db.refresh(assignment)
    return assignment


# ==========================================================
# 🗑️ 5️⃣ Xóa bài tập
# ==========================================================
def delete_assignment(db: Session, assignment_id: str):
    """Xóa bài tập và file đính kèm (nếu có)"""
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        return False

    # Xóa file đính kèm nếu có
    files = db.query(AssignmentFile).filter(AssignmentFile.assignment_id == assignment_id).all()
    for f in files:
        db.delete(f)

    db.delete(assignment)
    db.commit()
    return True


# ==========================================================
# 📊 6️⃣ Thống kê tổng quan bài tập
# ==========================================================
def get_statistics(db: Session):
    """Thống kê tổng quan bài tập trong hệ thống"""
    total_assignments = db.query(func.count(Assignment.id)).scalar()
    total_submissions = db.query(func.count(AssignmentSubmission.id)).scalar()
    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.status == "graded")
        .scalar()
    )

    return {
        "total_assignments": total_assignments or 0,
        "total_submissions": total_submissions or 0,
        "graded": graded or 0,
    }
