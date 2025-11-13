"""
==========================================================
🧠 SERVICE: Teacher - Quiz Service
Xử lý logic nghiệp vụ cho việc quản lý Quiz của giáo viên
==========================================================
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
from datetime import datetime
import uuid

# ✅ Import model
from app.models.quiz import Quiz
from app.models.course import Course
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User


# ======================================================
# ⚙️ HÀM HỖ TRỢ
# ======================================================
def generate_uuid() -> str:
    """Tạo UUID ngẫu nhiên"""
    return str(uuid.uuid4())


# ======================================================
# 📋 1️⃣ Lấy danh sách quiz của giáo viên
# ======================================================
def get_quizzes_by_teacher(db: Session, teacher_id: str):
    """
    Trả về danh sách tất cả quiz thuộc các khóa học mà giáo viên sở hữu.
    """
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .order_by(Quiz.created_at.desc())
        .all()
    )


# ======================================================
# 🔍 2️⃣ Lấy chi tiết quiz theo ID (xác thực quyền)
# ======================================================
def get_quiz_by_id(db: Session, quiz_id: str, teacher_id: str):
    """Lấy quiz cụ thể của giáo viên"""
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(and_(Quiz.id == quiz_id, Course.teacher_id == teacher_id))
        .options(joinedload(Quiz.course))
        .first()
    )


# ======================================================
# ➕ 3️⃣ Tạo quiz mới
# ======================================================
def create_quiz(
    db: Session,
    teacher_id: str,
    course_id: str,
    title: str,
    description: str = "",
    quiz_type: str = "practice",
    difficulty_level: str = "medium",
    time_limit_minutes: int = None,
    max_attempts: int = 1,
    passing_score: float = 60.0,
    total_questions: int = 10,
    available_from: datetime = None,
    available_to: datetime = None,
):
    """Tạo quiz mới cho khóa học của giáo viên"""
    quiz = Quiz(
        id=generate_uuid(),
        title=title.strip(),
        description=description.strip() if description else None,
        quiz_type=quiz_type,
        difficulty_level=difficulty_level,
        time_limit_minutes=time_limit_minutes,
        max_attempts=max_attempts,
        passing_score=passing_score,
        total_questions=total_questions,
        course_id=course_id,
        available_from=available_from,
        available_to=available_to,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


# ======================================================
# ✏️ 4️⃣ Cập nhật quiz
# ======================================================
def update_quiz(
    db: Session,
    teacher_id: str,
    quiz_id: str,
    course_id: str,
    title: str,
    description: str,
    quiz_type: str,
    difficulty_level: str,
    time_limit_minutes: int,
    max_attempts: int,
    passing_score: float,
    total_questions: int,
    available_from: datetime = None,
    available_to: datetime = None,
):
    """Cập nhật quiz (nếu giáo viên sở hữu)"""
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(and_(Quiz.id == quiz_id, Course.teacher_id == teacher_id))
        .first()
    )
    if not quiz:
        return None

    quiz.course_id = course_id
    quiz.title = title.strip()
    quiz.description = description.strip() if description else None
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


# ======================================================
# 🗑️ 5️⃣ Xóa quiz
# ======================================================
def delete_quiz(db: Session, teacher_id: str, quiz_id: str):
    """Xóa quiz nếu thuộc quyền sở hữu của giáo viên"""
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(and_(Quiz.id == quiz_id, Course.teacher_id == teacher_id))
        .first()
    )
    if not quiz:
        return False

    db.delete(quiz)
    db.commit()
    return True


# ======================================================
# 📊 6️⃣ Lấy quiz kèm câu hỏi
# ======================================================
def get_quiz_detail(db: Session, teacher_id: str, quiz_id: str):
    """
    Lấy quiz + danh sách câu hỏi (Question, QuestionOption)
    """
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(and_(Quiz.id == quiz_id, Course.teacher_id == teacher_id))
        .options(
            joinedload(Quiz.course),
            joinedload(Quiz.questions).joinedload(Question.options),
        )
        .first()
    )


# ======================================================
# 📈 7️⃣ Thống kê kết quả học viên cho quiz
# ======================================================
def get_quiz_statistics(db: Session, teacher_id: str, quiz_id: str):
    """
    Lấy thống kê tổng hợp kết quả học viên cho quiz thuộc quyền của giáo viên:
    - Tổng số lượt làm
    - Số học viên tham gia
    - Điểm trung bình
    - Số đạt / không đạt
    - Top 5 học viên điểm cao nhất
    """
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(and_(Quiz.id == quiz_id, Course.teacher_id == teacher_id))
        .first()
    )
    if not quiz:
        return None

    stats = (
        db.query(
            func.count(QuizAttempt.id).label("total_attempts"),
            func.count(func.distinct(QuizAttempt.user_id)).label("unique_students"),
            func.avg(QuizAttempt.score).label("avg_score"),
            func.sum(func.case((QuizAttempt.score >= quiz.passing_score, 1), else_=0)).label("passed"),
            func.sum(func.case((QuizAttempt.score < quiz.passing_score, 1), else_=0)).label("failed"),
        )
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == "submitted")
        .first()
    )

    top_students = (
        db.query(
            User.full_name,
            QuizAttempt.score,
            QuizAttempt.attempt_number,
            QuizAttempt.submitted_at,
        )
        .join(User, QuizAttempt.user_id == User.id)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == "submitted")
        .order_by(QuizAttempt.score.desc())
        .limit(5)
        .all()
    )

    return {
        "quiz": quiz,
        "stats": stats,
        "top_students": top_students,
    }
