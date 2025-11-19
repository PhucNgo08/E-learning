"""
=====================================================
📘 QUIZ SERVICE
Cung cấp các chức năng CRUD và sinh quiz từ ngân hàng câu hỏi.
=====================================================
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.question_bank import QuestionBank


# =====================================================
# 🧩 1️⃣ Lấy danh sách quiz
# =====================================================
def get_all_quizzes(db: Session):
    """Lấy tất cả quiz từ CSDL."""
    return db.query(Quiz).order_by(Quiz.created_at.desc()).all()


def get_quiz_by_id(db: Session, quiz_id: str):
    """Tìm quiz theo ID."""
    return db.query(Quiz).filter(Quiz.id == quiz_id).first()


# =====================================================
# ➕ 2️⃣ Tạo quiz mới
# =====================================================
def create_quiz(
    db: Session,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    total_questions: int,
    time_limit_minutes: int = None,
    passing_score: float = 60.0,
    course_id: str = None,
    lesson_id: str = None
):
    """Tạo mới một quiz thủ công."""
    try:
        quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            quiz_type=quiz_type,
            difficulty_level=difficulty_level,
            total_questions=total_questions,
            time_limit_minutes=time_limit_minutes,
            passing_score=passing_score,
            course_id=course_id,
            lesson_id=lesson_id,
            created_at=datetime.utcnow(),
        )

        db.add(quiz)
        db.commit()
        db.refresh(quiz)
        return quiz
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi tạo quiz: {str(e)}") from e


# =====================================================
# ✏️ 3️⃣ Cập nhật quiz
# =====================================================
def update_quiz(
    db: Session,
    quiz_id: str,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    total_questions: int,
    time_limit_minutes: int,
    passing_score: float
):
    """Cập nhật quiz."""
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise ValueError("Không tìm thấy quiz.")

    quiz.title = title
    quiz.description = description
    quiz.quiz_type = quiz_type
    quiz.difficulty_level = difficulty_level
    quiz.total_questions = total_questions
    quiz.time_limit_minutes = time_limit_minutes
    quiz.passing_score = passing_score
    quiz.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(quiz)
        return quiz
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi cập nhật quiz: {str(e)}") from e


# =====================================================
# ❌ 4️⃣ Xóa quiz
# =====================================================
def delete_quiz(db: Session, quiz_id: str):
    """Xóa quiz và tất cả câu hỏi liên quan."""
    quiz = get_quiz_by_id(db, quiz_id)
    if not quiz:
        raise ValueError("Không tìm thấy quiz cần xóa.")

    try:
        # Xóa câu hỏi trước để tránh lỗi khóa ngoại
        db.query(Question).filter(Question.quiz_id == quiz_id).delete()
        db.delete(quiz)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi xóa quiz: {str(e)}") from e


# =====================================================
# 🧠 5️⃣ Sinh quiz tự động từ ngân hàng câu hỏi
# =====================================================
def generate_quiz_from_bank(
    db: Session,
    title: str,
    description: str,
    difficulty_level: str,
    total_questions: int,
    course_id: str = None
):
    """
    Tự động sinh quiz từ bảng QuestionBank dựa trên độ khó và số lượng.
    """
    try:
        questions_bank = (
            db.query(QuestionBank)
            .filter(QuestionBank.difficulty_level == difficulty_level)
            .order_by(QuestionBank.created_at.desc())
            .limit(total_questions)
            .all()
        )

        if not questions_bank or len(questions_bank) < total_questions:
            raise ValueError("Không đủ câu hỏi trong ngân hàng để tạo quiz.")

        # Tạo quiz mới
        new_quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            quiz_type="auto",
            difficulty_level=difficulty_level,
            total_questions=total_questions,
            course_id=course_id,
            created_at=datetime.utcnow(),
        )
        db.add(new_quiz)
        db.flush()  # Lấy ID quiz ngay

        # Tạo câu hỏi từ ngân hàng
        for q in questions_bank:
            question = Question(
                id=str(uuid.uuid4()),
                quiz_id=new_quiz.id,
                question_type=q.question_type,
                question_text=q.question_text,
                explanation=q.explanation,
                points=q.points,
                difficulty_level=q.difficulty_level,
                created_at=datetime.utcnow(),
            )
            db.add(question)

            # Tạo các lựa chọn
            if hasattr(q, "options") and q.options:
                for opt in q.options:
                    db.add(
                        QuestionOption(
                            id=str(uuid.uuid4()),
                            question_id=question.id,
                            option_text=opt.option_text,
                            is_correct=opt.is_correct,
                            created_at=datetime.utcnow(),
                        )
                    )

        db.commit()
        db.refresh(new_quiz)
        return new_quiz

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi khi sinh quiz tự động: {str(e)}") from e


# =====================================================
# 🧾 6️⃣ Lấy danh sách câu hỏi của quiz
# =====================================================
def get_questions_by_quiz(db: Session, quiz_id: str):
    """Lấy tất cả câu hỏi thuộc quiz."""
    return (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.created_at.asc())
        .all()
    )
from app.models.course import Course
from app.models.user import User
from sqlalchemy.orm import joinedload

def get_all_quizzes_for_admin(db: Session):
    """
    Lấy tất cả quiz + tên khóa học + tên giáo viên.
    Dùng cho Admin xem danh sách đầy đủ.
    """
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .join(User, Course.teacher_id == User.id)
        .options(
            joinedload(Quiz.course).joinedload(Course.teacher)
        )
        .order_by(Quiz.created_at.desc())
        .all()
    )
