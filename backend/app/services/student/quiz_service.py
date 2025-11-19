"""
==========================================================
📘 SERVICE: Student - Quiz (PRODUCTION READY V2)
Dành cho Quiz kiểu PRACTICE (không bao gồm exam graded)
==========================================================
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import uuid
import random
import traceback

from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from app.models.lesson_progress import LessonProgress


# ======================================================
# 📗 1) LẤY DANH SÁCH QUIZ PRACTICE
# ======================================================
def get_all_quizzes_for_student(db: Session):
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                Quiz.quiz_type == "practice",                     # ⭐ FIX
                Quiz.status == "published",
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except:
        traceback.print_exc()
        return []


# ======================================================
# 📘 2) QUIZ PRACTICE THEO KHÓA HỌC
# ======================================================
def get_quizzes_by_course(db: Session, course_id: str):
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                Quiz.quiz_type == "practice",                     # ⭐ FIX
                Quiz.course_id == course_id,
                Quiz.status == "published",
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except:
        traceback.print_exc()
        return []


# ======================================================
# 🧩 3) LẤY QUIZ + CÂU HỎI + OPTIONS
# ======================================================
def get_quiz_with_questions(db: Session, quiz_id: str):
    try:
        quiz = (
            db.query(Quiz)
            .options(joinedload(Quiz.questions).joinedload(Question.options))
            .filter(Quiz.id == quiz_id, Quiz.quiz_type == "practice")   # ⭐ FIX
            .first()
        )

        if not quiz:
            return None

        # Random câu hỏi
        if quiz.randomize_questions:
            quiz.questions = list(quiz.questions)
            random.shuffle(quiz.questions)

        # Random đáp án
        if quiz.randomize_options:
            for q in quiz.questions:
                q.options = list(q.options)
                random.shuffle(q.options)

        return quiz

    except:
        traceback.print_exc()
        return None


# ======================================================
# ⛔ 4) CHỐNG DOUBLE SUBMIT
# ======================================================
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


# ======================================================
# 📝 5) NỘP BÀI QUIZ PRACTICE
# ======================================================
def submit_quiz(db: Session, quiz_id: str, form_data: dict, user_id: str):
    try:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return {"error": "Quiz không tồn tại"}

        # ===== Chống spam =====
        if has_recent_attempt(db, user_id, quiz_id):
            return {"error": "Đang xử lý bài làm… vui lòng đợi 1–2 giây."}

        # ===== Check số lần làm =====
        prev = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
            .count()
        )
        if quiz.max_attempts and prev >= quiz.max_attempts:
            return {"error": "Bạn đã hết lượt làm bài."}

        attempt_number = prev + 1
        started_at = datetime.fromisoformat(form_data["started_at"]) if "started_at" in form_data else datetime.utcnow()
        submitted_at = datetime.utcnow()

        attempt_id = str(uuid.uuid4())
        attempt = QuizAttempt(
            id=attempt_id,
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_number=attempt_number,
            status="submitted",
            started_at=started_at,
            submitted_at=submitted_at,
        )
        db.add(attempt)
        db.flush()

        # ===== Chấm điểm =====
        total_points = 0
        earned_points = 0
        correct_count = 0

        for q in quiz.questions:
            qid = str(q.id)
            selected = form_data.get(f"question_{qid}", None)

            total_points += float(q.points or 1)

            option = None
            if selected:
                option = db.query(QuestionOption).filter(QuestionOption.id == selected).first()

            is_correct = bool(option and option.is_correct)
            if is_correct:
                earned_points += float(q.points or 1)
                correct_count += 1

            db.add(
                AttemptAnswer(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_id,
                    question_id=qid,
                    selected_option_id=selected,
                    is_correct=is_correct,
                    points_earned=float(q.points or 1) if is_correct else 0,
                )
            )

        score = round((earned_points / max(total_points, 1)) * 100, 2)
        time_spent = int((submitted_at - started_at).total_seconds())

        attempt.score = score
        attempt.correct_answers = correct_count
        attempt.total_questions = len(quiz.questions)      # ⭐ FIX
        attempt.time_spent_seconds = time_spent

        db.commit()
        db.refresh(attempt)

        return {"attempt_id": attempt_id, "score": score}

    except:
        db.rollback()
        traceback.print_exc()
        return {"error": "Lỗi khi nộp bài, vui lòng thử lại."}


# ======================================================
# 🎯 6) LẤY KẾT QUẢ CHI TIẾT
# ======================================================
def get_quiz_result(db: Session, attempt_id: str):
    try:
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
    except:
        traceback.print_exc()
        return None


# ======================================================
# 🕓 7) LỊCH SỬ LÀM QUIZ
# ======================================================
def get_quiz_history_for_student(db: Session, user_id: str):
    try:
        return (
            db.query(QuizAttempt)
            .options(joinedload(QuizAttempt.quiz))
            .filter(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
    except:
        traceback.print_exc()
        return []


# ======================================================
# 🔎 8) LỊCH SỬ QUIZ THEO KHOÁ HỌC
# ======================================================
def get_quiz_history_for_student_by_course(db, user_id, course_id):
    try:
        return (
            db.query(QuizAttempt)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .filter(QuizAttempt.user_id == user_id, Quiz.course_id == course_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
    except:
        traceback.print_exc()
        return []


# ======================================================
# 📌 9) UTILS
# ======================================================
def get_quiz_attempt_count_for_student(db, user_id, quiz_id):
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .count()
        )
    except:
        return 0


def get_latest_quiz_attempt_for_student(db, user_id, quiz_id):
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.started_at.desc())
            .first()
        )
    except:
        return None
