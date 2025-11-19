"""
==========================================================
🧠 SERVICE: Exam Service (Teacher/Admin/Student)
Đồng bộ với Quiz Model (graded) – FINAL PRO MAX 2025
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
from datetime import datetime
import uuid

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User


# ============================================================
# 📌 1. Lấy danh sách bài thi theo ROLE
# ============================================================
def get_exams(db: Session, user_id: str, role: str):
    """
    ADMIN → xem tất cả graded
    TEACHER → xem graded thuộc khóa mình dạy
    STUDENT → xem graded đang mở + được duyệt + đã ghi danh
    """

    base = db.query(Quiz).filter(Quiz.quiz_type == "graded")

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------
    if role == "admin":
        return base.order_by(Quiz.created_at.desc()).all()

    # --------------------------------------------------------
    # TEACHER
    # --------------------------------------------------------
    if role == "teacher":
        return (
            base.join(Course, Quiz.course_id == Course.id)
            .filter(Course.teacher_id == user_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )

    # --------------------------------------------------------
    # STUDENT
    # --------------------------------------------------------
    if role == "student":
        now = datetime.utcnow()

        return (
            base.join(Course, Quiz.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.enrollment_status.in_(["active", "approved", "completed"]),

                Quiz.is_approved == True,
                Quiz.status == "published",

                Quiz.available_from != None,
                Quiz.available_to != None,
                Quiz.available_from <= now,
                Quiz.available_to >= now,
            )
            .order_by(Quiz.available_from.asc())
            .all()
        )

    return []


# ============================================================
# 📌 2. Validate dữ liệu exam
# ============================================================
def validate_exam_inputs(total_questions, time_limit, max_attempts,
                         passing_score, available_from, available_to):

    if total_questions <= 0:
        raise ValueError("Số câu hỏi phải lớn hơn 0.")
    if time_limit <= 0:
        raise ValueError("Thời gian làm bài phải lớn hơn 0.")
    if max_attempts <= 0:
        raise ValueError("Số lần làm bài tối thiểu phải là 1.")
    if not (0 <= passing_score <= 100):
        raise ValueError("Điểm qua môn phải từ 0 đến 100.")

    if available_from and available_to:
        if available_to <= available_from:
            raise ValueError("Thời gian đóng phải lớn hơn thời gian mở.")


# ============================================================
# 📌 3. Check teacher có sở hữu bài thi không?
# ============================================================
def is_teacher_owner(db: Session, teacher_id: str, exam_id: str) -> bool:
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == exam_id, Course.teacher_id == teacher_id)
        .first()
        is not None
    )


# ============================================================
# 📌 4. Tạo bài thi (graded)
# ============================================================
def create_exam(
    db: Session,
    user_id: str,
    role: str,
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
    # --------------------------------------------------------
    # TEACHER → phải sở hữu khoá học
    # --------------------------------------------------------
    if role == "teacher":
        course = db.query(Course).filter(
            Course.id == course_id,
            Course.teacher_id == user_id
        ).first()
        if not course:
            raise PermissionError("Bạn không có quyền tạo bài thi cho khóa này.")
    else:
        course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise ValueError("Khóa học không tồn tại.")

    # Validate input
    validate_exam_inputs(
        total_questions, time_limit, max_attempts,
        passing_score, available_from, available_to
    )

    # --------------------------------------------------------
    # TẠO EXAM
    # --------------------------------------------------------
    try:
        exam = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description.strip() if description else None,

            course_id=course_id,
            quiz_type="graded",

            total_questions=total_questions,
            time_limit_minutes=time_limit,
            max_attempts=max_attempts,
            passing_score=passing_score,

            available_from=available_from,
            available_to=available_to,

            show_correct_answers=False,
            randomize_questions=True,
            randomize_options=True,

            status="pending",
            is_approved=False,

            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi tạo bài thi: {str(e)}")


# ============================================================
# 📌 5. Cập nhật bài thi
# ============================================================
def update_exam(
    db: Session,
    user_id: str,
    role: str,
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
        raise ValueError("Không tìm thấy bài thi.")

    # Role kiểm tra
    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không có quyền sửa bài thi này.")

    # Validate
    validate_exam_inputs(
        total_questions, time_limit, max_attempts,
        passing_score, available_from, available_to
    )

    try:
        exam.title = title.strip()
        exam.description = description.strip() if description else None

        exam.total_questions = total_questions
        exam.time_limit_minutes = time_limit
        exam.max_attempts = max_attempts
        exam.passing_score = passing_score

        exam.available_from = available_from
        exam.available_to = available_to

        exam.status = "pending"
        exam.is_approved = False
        exam.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi cập nhật bài thi: {str(e)}")


# ============================================================
# 📌 6. Xóa bài thi
# ============================================================
def delete_exam(db: Session, user_id: str, role: str, exam_id: str):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không có quyền xóa bài thi này.")

    try:
        # Xóa options
        db.query(QuestionOption).filter(
            QuestionOption.question_id.in_(
                db.query(Question.id).filter(Question.quiz_id == exam_id)
            )
        ).delete(synchronize_session=False)

        # Xóa câu hỏi
        db.query(Question).filter(
            Question.quiz_id == exam_id
        ).delete(synchronize_session=False)

        # Xóa exam
        db.delete(exam)
        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi xóa bài thi: {str(e)}")


# ============================================================
# 📌 7. Admin duyệt bài thi
# ============================================================
def approve_exam(db: Session, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()

    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    exam.is_approved = True
    exam.status = "published"
    exam.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(exam)
    return exam


# ============================================================
# 📌 8. Admin từ chối bài thi
# ============================================================
def reject_exam(db: Session, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()

    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    exam.is_approved = False
    exam.status = "rejected"
    exam.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(exam)
    return exam


# ============================================================
# 📌 9. Đếm số lần student làm bài thi
# ============================================================
def get_student_attempt_count(db: Session, user_id: str, exam_id: str):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id,
                QuizAttempt.quiz_id == exam_id)
        .count()
    )
