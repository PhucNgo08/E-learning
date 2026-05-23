"""
Dịch vụ quản lý kỳ thi/bài kiểm tra.
Đã chỉnh để khớp enum trong model:
- quiz_type: practice, graded, survey
- status: draft, published, archived
"""

import uuid
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.question import Question
from app.models.question_bank import QuestionBank
from app.models.question_option import QuestionOption
from app.models.quiz import Quiz


VALID_QUIZ_TYPES = {"practice", "graded", "survey"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_STATUSES = {"draft", "published", "archived"}


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _validate_quiz_core(quiz_type: str, difficulty_level: str, status: str = "published"):
    if quiz_type not in VALID_QUIZ_TYPES:
        raise ValueError("Loại kỳ thi không hợp lệ.")
    if difficulty_level not in VALID_DIFFICULTIES:
        raise ValueError("Độ khó không hợp lệ.")
    if status not in VALID_STATUSES:
        raise ValueError("Trạng thái kỳ thi không hợp lệ.")


def get_all_quizzes(db: Session):
    return db.query(Quiz).order_by(Quiz.created_at.desc()).all()


def get_quiz_by_id(db: Session, quiz_id: str):
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()


def create_quiz(
    db: Session,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    total_questions: int,
    time_limit_minutes: int | None = None,
    passing_score: float = 60.0,
    course_id: str | None = None,
    lesson_id: str | None = None,
    status: str = "published",
):
    _validate_quiz_core(quiz_type, difficulty_level, status)

    if not _clean(title):
        raise ValueError("Tiêu đề kỳ thi không được để trống.")

    try:
        quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=_clean(description),
            quiz_type=quiz_type,
            difficulty_level=difficulty_level,
            total_questions=max(int(total_questions or 0), 0),
            time_limit_minutes=time_limit_minutes,
            passing_score=passing_score,
            course_id=course_id,
            lesson_id=lesson_id,
            status=status,
            is_approved=(status == "published"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        return quiz
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo kỳ thi: {str(e)}") from e


def update_quiz(
    db: Session,
    quiz_id: str,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    total_questions: int,
    time_limit_minutes: int | None,
    passing_score: float,
    status: str = "published",
):
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise ValueError("Không tìm thấy kỳ thi.")

    _validate_quiz_core(quiz_type, difficulty_level, status)

    quiz.title = title.strip()
    quiz.description = _clean(description)
    quiz.quiz_type = quiz_type
    quiz.difficulty_level = difficulty_level
    quiz.total_questions = max(int(total_questions or 0), 0)
    quiz.time_limit_minutes = time_limit_minutes
    quiz.passing_score = passing_score
    quiz.status = status
    quiz.is_approved = (status == "published")
    quiz.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(quiz)
        return quiz
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật kỳ thi: {str(e)}") from e


def delete_quiz(db: Session, quiz_id: str):
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise ValueError("Không tìm thấy kỳ thi cần xóa.")

    try:
        # Không xóa Question bằng bulk delete vì có thể làm lỗi khóa ngoại attempt_answers.
        # Dùng ORM cascade của Quiz -> Question/QuestionOption/QuizAttempt/AttemptAnswer.
        db.delete(quiz)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa kỳ thi: {str(e)}") from e


def generate_quiz_from_bank(
    db: Session,
    title: str,
    description: str,
    difficulty_level: str,
    total_questions: int,
    course_id: str | None = None,
):
    """
    Sinh kỳ thi từ ngân hàng câu hỏi.
    Lưu ý nghiệp vụ: model Quiz không có quiz_type='auto', nên dùng 'practice'.
    """
    if difficulty_level not in VALID_DIFFICULTIES:
        raise ValueError("Độ khó không hợp lệ.")

    try:
        questions_bank = (
            db.query(QuestionBank)
            .filter(QuestionBank.difficulty_level == difficulty_level)
            .order_by(QuestionBank.created_at.desc())
            .limit(total_questions)
            .all()
        )

        if not questions_bank or len(questions_bank) < total_questions:
            raise ValueError("Không đủ câu hỏi trong ngân hàng để tạo kỳ thi.")

        new_quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=_clean(description),
            quiz_type="practice",
            difficulty_level=difficulty_level,
            total_questions=0,
            course_id=course_id,
            status="draft",
            is_approved=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_quiz)
        db.flush()

        count = 0
        for order, q in enumerate(questions_bank, start=1):
            question = Question(
                id=str(uuid.uuid4()),
                quiz_id=new_quiz.id,
                question_type=getattr(q, "question_type", "multiple_choice") or "multiple_choice",
                question_text=q.question_text,
                explanation=getattr(q, "explanation", None),
                points=getattr(q, "points", 1.0) or 1.0,
                difficulty_level=q.difficulty_level,
                question_order=order,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(question)
            db.flush()
            count += 1

            if hasattr(q, "options") and q.options:
                for opt_order, opt in enumerate(q.options, start=1):
                    db.add(
                        QuestionOption(
                            id=str(uuid.uuid4()),
                            question_id=question.id,
                            option_text=opt.option_text,
                            is_correct=bool(opt.is_correct),
                            option_order=opt_order,
                            created_at=datetime.utcnow(),
                        )
                    )

        new_quiz.total_questions = count
        db.commit()
        db.refresh(new_quiz)
        return new_quiz

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi sinh kỳ thi tự động: {str(e)}") from e


def get_questions_by_quiz(db: Session, quiz_id: str):
    return (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.question_order.asc(), Question.created_at.asc())
        .all()
    )


def get_all_quizzes_for_admin(db: Session):
    """
    Lấy tất cả kỳ thi. Không dùng inner join để tránh mất kỳ thi nếu khóa học/giảng viên bị thiếu.
    """
    return (
        db.query(Quiz)
        .options(joinedload(Quiz.course).joinedload(Course.teacher))
        .order_by(Quiz.created_at.desc())
        .all()
    )
