from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import uuid

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.question_bank import QuestionBank


# ============================================================
# 📋 Lấy danh sách kỳ thi (graded)
# ============================================================
def get_all_exams(db: Session):
    try:
        return (
            db.query(Quiz)
            .filter(Quiz.quiz_type == "graded")
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy danh sách kỳ thi: {str(e)}")


# ============================================================
# 🔍 Validate dữ liệu chung cho kỳ thi
# ============================================================
def validate_exam_inputs(
    total_questions: int,
    time_limit: int,
    max_attempts: int,
    passing_score: float,
    available_from,
    available_to,
):
    if total_questions <= 0:
        raise ValueError("Số câu hỏi phải lớn hơn 0.")

    if time_limit <= 0:
        raise ValueError("Thời gian làm bài phải lớn hơn 0.")

    if max_attempts <= 0:
        raise ValueError("Số lần làm bài phải ít nhất 1.")

    if not (0 <= passing_score <= 100):
        raise ValueError("Điểm qua môn phải nằm trong khoảng 0–100.")

    if available_from and available_to and available_to <= available_from:
        raise ValueError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu.")


# ============================================================
# ➕ Tạo kỳ thi mới
# ============================================================
def create_exam(
    db: Session,
    title: str,
    description: str,
    course_id: str,
    total_questions: int,
    time_limit: int,
    max_attempts: int,
    passing_score: float,
    available_from,
    available_to,
):

    # validate course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Khóa học không tồn tại.")

    # validate logic
    validate_exam_inputs(
        total_questions, time_limit, max_attempts, passing_score, available_from, available_to
    )

    # check question bank
    available_questions = (
        db.query(QuestionBank)
        .filter(QuestionBank.created_by == course.teacher_id)
        .count()
    )

    if total_questions > available_questions:
        raise ValueError(
            f"Không đủ câu hỏi. Hiện có {available_questions}, yêu cầu {total_questions}."
        )

    # create quiz
    try:
        exam = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=(description or "").strip(),
            course_id=course_id,
            total_questions=total_questions,
            time_limit_minutes=time_limit,
            max_attempts=max_attempts,
            passing_score=passing_score,
            quiz_type="graded",
            show_correct_answers=False,
            randomize_questions=True,
            randomize_options=True,
            available_from=available_from,
            available_to=available_to,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo kỳ thi: {str(e)}")


# ============================================================
# ✏️ Cập nhật kỳ thi
# ============================================================
def update_exam(
    db: Session,
    exam_id: str,
    title: str,
    description: str,
    total_questions: int,
    time_limit: int,
    max_attempts: int,
    passing_score: float,
    available_from,
    available_to,
):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy kỳ thi.")

    validate_exam_inputs(
        total_questions, time_limit, max_attempts, passing_score, available_from, available_to
    )

    try:
        exam.title = title.strip()
        exam.description = (description or "").strip()
        exam.total_questions = total_questions
        exam.time_limit_minutes = time_limit
        exam.max_attempts = max_attempts
        exam.passing_score = passing_score
        exam.available_from = available_from
        exam.available_to = available_to
        exam.quiz_type = "graded"
        exam.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật kỳ thi: {str(e)}")


# ============================================================
# ❌ Xóa kỳ thi
# ============================================================
def delete_exam(db: Session, exam_id: str):
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
