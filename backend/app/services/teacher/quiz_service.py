"""
==============================================================
🧠 SERVICE: Teacher - Quiz Service
Đồng bộ với router teacher_quiz.py
Fix quyền giáo viên + thống kê top student theo user_profiles
==============================================================
"""

from datetime import datetime
import uuid

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User
from app.models.user_profile import UserProfile


# ============================================================
# Utility
# ============================================================
def generate_uuid() -> str:
    return str(uuid.uuid4())


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


# ============================================================
# 1) Lấy danh sách quiz của giáo viên
# ============================================================
def get_quizzes_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .order_by(Quiz.created_at.desc())
        .all()
    )


# ============================================================
# 2) Lấy quiz theo ID
# ============================================================
def get_quiz_by_id(db: Session, quiz_id: str, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(
            Quiz.id == quiz_id,
            Course.teacher_id == teacher_id,
        )
        .options(joinedload(Quiz.course))
        .first()
    )


# ============================================================
# 3) Tạo Quiz mới
# ============================================================
def create_quiz(
    db: Session,
    teacher_id: str,
    course_id: str,
    title: str,
    description: str = "",
    quiz_type: str = "practice",
    difficulty_level: str = "medium",
    time_limit_minutes: int | None = None,
    max_attempts: int = 1,
    passing_score: float = 60.0,
    total_questions: int = 10,
    available_from: datetime | None = None,
    available_to: datetime | None = None,
    status: str = "published",
    is_approved: bool = True,
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not course:
        raise PermissionError("Bạn không có quyền tạo quiz trong khóa học này")

    try:
        quiz = Quiz(
            id=generate_uuid(),
            title=title.strip(),
            description=_clean_text(description),
            quiz_type=quiz_type,
            difficulty_level=difficulty_level,
            time_limit_minutes=time_limit_minutes,
            max_attempts=max_attempts,
            passing_score=passing_score,
            total_questions=total_questions,
            course_id=course_id,
            available_from=available_from,
            available_to=available_to,
            status=status,
            is_approved=is_approved,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        return quiz
    except Exception:
        db.rollback()
        raise


# ============================================================
# 4) Sửa Quiz
# ============================================================
def update_quiz(
    db: Session,
    teacher_id: str,
    quiz_id: str,
    course_id: str,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    time_limit_minutes: int | None,
    max_attempts: int,
    passing_score: float,
    total_questions: int,
    available_from: datetime | None = None,
    available_to: datetime | None = None,
):
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return None

    target_course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not target_course:
        raise PermissionError("Bạn không có quyền chuyển quiz sang khóa học này")

    try:
        quiz.course_id = course_id
        quiz.title = title.strip()
        quiz.description = _clean_text(description)
        quiz.quiz_type = quiz_type
        quiz.difficulty_level = difficulty_level
        quiz.time_limit_minutes = time_limit_minutes
        quiz.max_attempts = max_attempts
        quiz.passing_score = passing_score
        quiz.total_questions = total_questions
        quiz.available_from = available_from
        quiz.available_to = available_to
        quiz.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(quiz)
        return quiz
    except Exception:
        db.rollback()
        raise


# ============================================================
# 5) Xoá Quiz
# ============================================================
def delete_quiz(db: Session, teacher_id: str, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return False

    try:
        db.query(QuestionOption).filter(
            QuestionOption.question_id.in_(
                db.query(Question.id).filter(Question.quiz_id == quiz_id)
            )
        ).delete(synchronize_session=False)

        db.query(Question).filter(Question.quiz_id == quiz_id).delete(
            synchronize_session=False
        )

        db.delete(quiz)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


# ============================================================
# 6) Chi tiết quiz + load câu hỏi
# ============================================================
def get_quiz_detail(db: Session, teacher_id: str, quiz_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(
            Quiz.id == quiz_id,
            Course.teacher_id == teacher_id,
        )
        .options(
            joinedload(Quiz.course),
            joinedload(Quiz.questions).joinedload(Question.options),
        )
        .first()
    )


# ============================================================
# 7) Thống kê quiz
# ============================================================
def get_quiz_statistics(db: Session, teacher_id: str, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return None

    stats = (
        db.query(
            func.count(QuizAttempt.id).label("total_attempts"),
            func.count(func.distinct(QuizAttempt.user_id)).label("unique_students"),
            func.avg(QuizAttempt.score).label("avg_score"),
            func.sum(
                case((QuizAttempt.score >= quiz.passing_score, 1), else_=0)
            ).label("passed"),
            func.sum(
                case((QuizAttempt.score < quiz.passing_score, 1), else_=0)
            ).label("failed"),
        )
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "submitted",
        )
        .first()
    )

    top_students = (
        db.query(
            UserProfile.full_name.label("full_name"),
            QuizAttempt.score,
            QuizAttempt.attempt_number,
            QuizAttempt.submitted_at,
        )
        .join(User, User.id == QuizAttempt.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "submitted",
        )
        .order_by(QuizAttempt.score.desc(), QuizAttempt.submitted_at.asc())
        .limit(5)
        .all()
    )

    return {
        "quiz": quiz,
        "stats": stats,
        "top_students": top_students,
    }