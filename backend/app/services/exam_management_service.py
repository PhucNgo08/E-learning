from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.quiz import Quiz
from datetime import datetime
import uuid

# 📋 Lấy danh sách kỳ thi
def get_all_exams(db: Session):
    try:
        return db.query(Quiz).order_by(Quiz.created_at.desc()).all()
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách kỳ thi: {str(e)}")


# ➕ Tạo kỳ thi mới
def create_exam(title: str, description: str, course_id: str, total_questions: int, db: Session):
    try:
        new_exam = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description or "",
            course_id=course_id,
            total_questions=total_questions or 10,
            created_at=datetime.utcnow(),
            quiz_type="graded"
        )
        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)
        return new_exam
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo kỳ thi: {str(e)}")


# ✏️ Cập nhật kỳ thi
def update_exam(exam_id: str, title: str, description: str, db: Session):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy kỳ thi.")
    try:
        exam.title = title.strip()
        exam.description = description
        exam.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(exam)
        return exam
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật kỳ thi: {str(e)}")


# ❌ Xóa kỳ thi
def delete_exam(exam_id: str, db: Session):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy kỳ thi.")
    try:
        db.delete(exam)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa kỳ thi: {str(e)}")
