"""
=================================================================
🧠 QUIZ SERVICE v12 – FINAL PRO MAX 2025
Dành cho: Teacher + Admin + Student
Tối ưu theo database E-Learning 2025 (31 bảng)
=================================================================
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, and_, or_
from datetime import datetime
import uuid
import random

# ============================
# Models
# ============================
from app.models.quiz import Quiz
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from app.models.user import User


# ============================================================
# Utility
# ============================================================
def generate_uuid():
    return str(uuid.uuid4())


# ===================================================================
# 🔵 TEACHER SERVICE – CRUD + STATISTICS + IMPORT-FRIENDLY
# ===================================================================

# ------------------------------------------------------------
# Lấy danh sách quiz của giáo viên
# ------------------------------------------------------------
def get_quizzes_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .order_by(Quiz.created_at.desc())
        .all()
    )


# ------------------------------------------------------------
# Lấy quiz theo ID (KHÔNG chặn import preview)
# ------------------------------------------------------------
def get_quiz_by_id(db: Session, quiz_id: str, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .first()
    )


# ------------------------------------------------------------
# Create Quiz
# ------------------------------------------------------------
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
    status: str = "published",
    is_approved: bool = True,
):

    # Check teacher owns course
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not course:
        raise PermissionError("Bạn không có quyền tạo quiz trong khóa học này")

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
        status=status,
        is_approved=is_approved,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


# ------------------------------------------------------------
# Update Quiz
# ------------------------------------------------------------
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

    quiz = (
        db.query(Quiz)
        .join(Course)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
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


# ------------------------------------------------------------
# Delete Quiz
# ------------------------------------------------------------
def delete_quiz(db: Session, teacher_id: str, quiz_id: str):

    quiz = (
        db.query(Quiz)
        .join(Course)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return False

    # Delete options
    db.query(QuestionOption).filter(
        QuestionOption.question_id.in_(
            db.query(Question.id).filter(Question.quiz_id == quiz_id)
        )
    ).delete(synchronize_session=False)

    # Delete questions
    db.query(Question).filter(Question.quiz_id == quiz_id).delete(synchronize_session=False)

    db.delete(quiz)
    db.commit()
    return True


# ------------------------------------------------------------
# Quiz Detail
# ------------------------------------------------------------
def get_quiz_detail(db: Session, teacher_id: str, quiz_id: str):
    return (
        db.query(Quiz)
        .join(Course)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .options(
            joinedload(Quiz.course),
            joinedload(Quiz.questions).joinedload(Question.options)
        )
        .first()
    )


# ------------------------------------------------------------
# Quiz Statistics
# ------------------------------------------------------------
def get_quiz_statistics(db: Session, teacher_id: str, quiz_id: str):

    quiz = (
        db.query(Quiz)
        .join(Course)
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
            func.sum(case((QuizAttempt.score >= quiz.passing_score, 1), else_=0)).label("passed"),
            func.sum(case((QuizAttempt.score < quiz.passing_score, 1), else_=0)).label("failed"),
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
        .join(User, User.id == QuizAttempt.user_id)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.status == "submitted")
        .order_by(QuizAttempt.score.desc())
        .limit(5)
        .all()
    )

    return {
        "quiz": quiz,
        "stats": stats,
        "top_students": top_students
    }


# ===================================================================
# 🔶 EXAM SERVICE – ROLE ADMIN + TEACHER + STUDENT (graded)
# ===================================================================

def get_exams(db: Session, user_id: str, role: str):
    base = db.query(Quiz).filter(Quiz.quiz_type == "graded")

    if role == "admin":
        return base.order_by(Quiz.created_at.desc()).all()

    if role == "teacher":
        return (
            base.join(Course, Quiz.course_id == Course.id)
            .filter(Course.teacher_id == user_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )

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
                Quiz.available_from <= now,
                Quiz.available_to >= now,
            )
            .order_by(Quiz.available_from.asc())
            .all()
        )

    return []


def is_teacher_owner(db: Session, teacher_id: str, exam_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == exam_id, Course.teacher_id == teacher_id)
        .first()
        is not None
    )


def validate_exam_inputs(total_questions, time_limit, max_attempts,
                         passing_score, available_from, available_to):

    if total_questions <= 0:
        raise ValueError("Số câu hỏi phải lớn hơn 0.")

    if time_limit <= 0:
        raise ValueError("Thời gian làm bài phải lớn hơn 0.")

    if max_attempts <= 0:
        raise ValueError("Số lần tối thiểu phải >= 1.")

    if not (0 <= passing_score <= 100):
        raise ValueError("Điểm qua môn phải từ 0–100.")

    if available_from and available_to and available_to <= available_from:
        raise ValueError("Thời gian đóng phải > thời gian mở.")


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

    if role == "teacher":
        course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == user_id).first()
        if not course:
            raise PermissionError("Bạn không có quyền tạo bài thi cho khóa này.")
    else:
        course = db.query(Course).filter(Course.id == course_id).first()

    validate_exam_inputs(
        total_questions, time_limit, max_attempts,
        passing_score, available_from, available_to
    )

    exam = Quiz(
        id=generate_uuid(),
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
        status="pending",
        is_approved=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


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

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không có quyền sửa bài thi này.")

    validate_exam_inputs(
        total_questions, time_limit, max_attempts,
        passing_score, available_from, available_to
    )

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


def delete_exam(db: Session, user_id: str, role: str, exam_id: str):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không có quyền xóa bài thi này.")

    db.query(QuestionOption).filter(
        QuestionOption.question_id.in_(
            db.query(Question.id).filter(Question.quiz_id == exam_id)
        )
    ).delete(synchronize_session=False)

    db.query(Question).filter(Question.quiz_id == exam_id).delete(synchronize_session=False)

    db.delete(exam)
    db.commit()
    return True


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


def get_student_attempt_count(db: Session, user_id: str, exam_id: str):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == exam_id)
        .count()
    )


# ===================================================================
# 🟩 STUDENT SERVICE – PRACTICE QUIZ + SUBMISSION
# ===================================================================

# ------------------------------------------------------------
# Practice Quiz List
# ------------------------------------------------------------
def get_all_quizzes_for_student(db: Session):
    now = datetime.utcnow()
    return (
        db.query(Quiz)
        .filter(
            Quiz.quiz_type == "practice",
            Quiz.status == "published",
            or_(Quiz.available_from == None, Quiz.available_from <= now),
            or_(Quiz.available_to == None, Quiz.available_to >= now),
        )
        .order_by(Quiz.created_at.desc())
        .all()
    )


# ------------------------------------------------------------
# Practice Quiz theo khóa học
# ------------------------------------------------------------
def get_quizzes_by_course(db: Session, course_id: str):
    now = datetime.utcnow()
    return (
        db.query(Quiz)
        .filter(
            Quiz.quiz_type == "practice",
            Quiz.course_id == course_id,
            Quiz.status == "published",
            or_(Quiz.available_from == None, Quiz.available_from <= now),
            or_(Quiz.available_to == None, Quiz.available_to >= now),
        )
        .order_by(Quiz.created_at.desc())
        .all()
    )


# ------------------------------------------------------------
# Lấy quiz + câu hỏi
# ------------------------------------------------------------
def get_quiz_with_questions(db: Session, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .options(joinedload(Quiz.questions).joinedload(Question.options))
        .filter(Quiz.id == quiz_id, Quiz.quiz_type == "practice")
        .first()
    )
    if not quiz:
        return None

    if quiz.randomize_questions:
        quiz.questions = list(quiz.questions)
        random.shuffle(quiz.questions)

    if quiz.randomize_options:
        for q in quiz.questions:
            q.options = list(q.options)
            random.shuffle(q.options)

    return quiz


# ------------------------------------------------------------
# Anti-spam
# ------------------------------------------------------------
def has_recent_attempt(db: Session, user_id: str, quiz_id: str):
    latest = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
        .order_by(QuizAttempt.created_at.desc())
        .first()
    )
    if not latest:
        return False

    return (datetime.utcnow() - latest.created_at).total_seconds() < 2


# ------------------------------------------------------------
# Submit practice quiz
# ------------------------------------------------------------
def submit_quiz(db: Session, quiz_id: str, form_data: dict, user_id: str):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return {"error": "Quiz không tồn tại"}

    if has_recent_attempt(db, user_id, quiz_id):
        return {"error": "Vui lòng đợi 1–2 giây trước khi nộp lại."}

    prev = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .count()
    )
    if quiz.max_attempts and prev >= quiz.max_attempts:
        return {"error": "Bạn đã hết lượt làm bài."}

    attempt_id = generate_uuid()
    attempt = QuizAttempt(
        id=attempt_id,
        quiz_id=quiz_id,
        user_id=user_id,
        attempt_number=prev + 1,
        status="submitted",
        started_at=datetime.utcnow(),
        submitted_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.flush()

    total_points = 0
    earned = 0
    correct = 0

    for q in quiz.questions:
        qid = str(q.id)
        selected = form_data.get(f"question_{qid}", None)

        total_points += float(q.points or 1)
        option = db.query(QuestionOption).filter(QuestionOption.id == selected).first() if selected else None

        is_correct = bool(option and option.is_correct)

        if is_correct:
            earned += float(q.points or 1)
            correct += 1

        db.add(
            AttemptAnswer(
                id=generate_uuid(),
                attempt_id=attempt_id,
                question_id=qid,
                selected_option_id=selected,
                is_correct=is_correct,
                points_earned=float(q.points or 1) if is_correct else 0,
            )
        )

    score = round((earned / max(total_points, 1)) * 100, 2)

    attempt.score = score
    attempt.correct_answers = correct
    attempt.total_questions = len(quiz.questions)
    attempt.time_spent_seconds = 0

    db.commit()
    db.refresh(attempt)

    return {"attempt_id": attempt_id, "score": score}


# ------------------------------------------------------------
# Kết quả chi tiết
# ------------------------------------------------------------
def get_quiz_result(db: Session, attempt_id: str):
    return (
        db.query(QuizAttempt)
        .options(
            joinedload(QuizAttempt.quiz),
            joinedload(QuizAttempt.answers)
            .joinedload(AttemptAnswer.question)
            .joinedload(Question.options),
        )
        .filter(QuizAttempt.id == attempt_id)
        .first()
    )


# ------------------------------------------------------------
# Lịch sử quiz theo user
# ------------------------------------------------------------
def get_quiz_history_for_student(db: Session, user_id: str):
    return (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.quiz))
        .filter(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.started_at.desc())
        .all()
    )


def get_quiz_history_for_student_by_course(db: Session, user_id: str, course_id: str):
    return (
        db.query(QuizAttempt)
        .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
        .filter(QuizAttempt.user_id == user_id, Quiz.course_id == course_id)
        .order_by(QuizAttempt.started_at.desc())
        .all()
    )


def get_latest_quiz_attempt_for_student(db, user_id, quiz_id):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
        .order_by(QuizAttempt.started_at.desc())
        .first()
    )
# ------------------------------------------------------------
# ĐẾM số lần làm quiz của học sinh (practice hoặc graded)
# ------------------------------------------------------------
def get_quiz_attempt_count_for_student(db: Session, user_id: str, quiz_id: str):
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id == quiz_id
        )
        .count()
    )

# ------------------------------------------------------------
# LẤY TẤT CẢ QUIZ CỦA KHÓA HỌC HỌC VIÊN ĐÃ GHI DANH
# (Practice + Graded) — Không lọc thời gian / trạng thái
# ------------------------------------------------------------
def get_all_quizzes_for_student_enrolled(db: Session, student_id: str):
    """
    Lấy toàn bộ quiz (practice + graded)
    thuộc các khóa học mà học viên đã ghi danh.
    Không lọc trạng thái / thời gian – giống danh sách của giáo viên.
    """

    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == student_id,
            Enrollment.enrollment_status.in_(["active", "approved", "completed"])
        )
        .options(joinedload(Quiz.course))
        .order_by(Quiz.created_at.desc())
        .all()
    )
