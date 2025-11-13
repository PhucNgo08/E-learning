"""
==========================================================
📘 SERVICE: Student - Quiz
Xử lý logic quiz (trắc nghiệm) cho học viên
==========================================================
"""
from sqlalchemy.orm import Session, joinedload
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from datetime import datetime
import uuid
import traceback


# ======================================================
# 📗 LẤY DANH SÁCH QUIZ ĐANG HOẠT ĐỘNG
# ======================================================
def get_all_quizzes_for_student(db: Session):
    """Lấy danh sách toàn bộ quiz đang hoạt động."""
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_all_quizzes_for_student] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 📘 LẤY QUIZ THEO KHÓA HỌC
# ======================================================
def get_quizzes_by_course(db: Session, course_id: str):
    """Lấy danh sách quiz thuộc về một khóa học cụ thể."""
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                Quiz.course_id == course_id,
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_quizzes_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 🧩 LẤY QUIZ + DANH SÁCH CÂU HỎI + LỰA CHỌN
# ======================================================
def get_quiz_with_questions(db: Session, quiz_id: str):
    """Lấy thông tin quiz + danh sách câu hỏi (và các lựa chọn)."""
    try:
        return (
            db.query(Quiz)
            .options(joinedload(Quiz.questions).joinedload(Question.options))
            .filter(Quiz.id == quiz_id)
            .first()
        )
    except Exception as e:
        print("❌ [get_quiz_with_questions] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 📝 NỘP BÀI QUIZ
# ======================================================
def submit_quiz(db: Session, quiz_id: str, form_data: dict, user_id: str):
    """Xử lý khi sinh viên nộp bài quiz."""
    try:
        if not user_id:
            raise ValueError("❌ User ID không được để trống khi nộp bài quiz")

        attempt_id = str(uuid.uuid4())
        attempt = QuizAttempt(
            id=attempt_id,
            quiz_id=quiz_id,
            user_id=user_id,
            status="submitted",
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
        )
        db.add(attempt)
        db.flush()

        correct = 0
        total = 0

        for key, value in form_data.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                selected_id = value

                option = db.query(QuestionOption).filter(QuestionOption.id == selected_id).first()
                is_correct = bool(option and option.is_correct)
                total += 1
                if is_correct:
                    correct += 1

                db.add(AttemptAnswer(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_id,
                    question_id=question_id,
                    selected_option_id=selected_id,
                    is_correct=is_correct,
                    points_earned=1 if is_correct else 0,
                ))

        score = round((correct / max(total, 1)) * 100, 2)
        attempt.score = score
        attempt.correct_answers = correct
        attempt.total_questions = total
        attempt.duration_seconds = 0

        db.commit()
        db.refresh(attempt)

        print(f"✅ [submit_quiz] user={user_id}, quiz={quiz_id}, score={score}")
        return {"attempt_id": attempt_id, "score": score}

    except Exception as e:
        db.rollback()
        print("❌ [submit_quiz] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🎯 XEM KẾT QUẢ QUIZ
# ======================================================
def get_quiz_result(db: Session, attempt_id: str):
    """Lấy kết quả của một attempt (bao gồm danh sách câu trả lời)."""
    try:
        attempt = (
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
        return attempt
    except Exception as e:
        print("❌ [get_quiz_result] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🕓 CÁC HÀM LỊCH SỬ & TIỆN ÍCH
# ======================================================
def get_quiz_history_for_student(db: Session, user_id: str):
    """Lấy toàn bộ lịch sử làm bài của sinh viên."""
    try:
        return (
            db.query(QuizAttempt)
            .options(joinedload(QuizAttempt.quiz))
            .filter(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_quiz_history_for_student] Lỗi:", e)
        traceback.print_exc()
        return []


def get_quiz_history_for_student_by_course(db: Session, user_id: str, course_id: str):
    """Lịch sử làm quiz theo khóa học."""
    try:
        return (
            db.query(QuizAttempt)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .options(joinedload(QuizAttempt.quiz))
            .filter(QuizAttempt.user_id == user_id, Quiz.course_id == course_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_quiz_history_for_student_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


def get_quiz_attempt_count_for_student(db: Session, user_id: str, quiz_id: str):
    """Lấy số lần đã làm quiz của sinh viên."""
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .count()
        )
    except Exception as e:
        print("❌ [get_quiz_attempt_count_for_student] Lỗi:", e)
        traceback.print_exc()
        return 0


def has_student_attempted_quiz(db: Session, user_id: str, quiz_id: str):
    """Kiểm tra sinh viên đã làm quiz này chưa."""
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .first()
            is not None
        )
    except Exception as e:
        print("❌ [has_student_attempted_quiz] Lỗi:", e)
        traceback.print_exc()
        return False


def get_highest_score_for_student_quiz(db: Session, user_id: str, quiz_id: str):
    """Lấy điểm cao nhất sinh viên đạt được cho quiz."""
    try:
        highest = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.score.desc())
            .first()
        )
        return highest.score if highest else 0.0
    except Exception as e:
        print("❌ [get_highest_score_for_student_quiz] Lỗi:", e)
        traceback.print_exc()
        return 0.0


def get_latest_quiz_attempt_for_student(db: Session, user_id: str, quiz_id: str):
    """Lấy lần làm quiz mới nhất của sinh viên."""
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.started_at.desc())
            .first()
        )
    except Exception as e:
        print("❌ [get_latest_quiz_attempt_for_student] Lỗi:", e)
        traceback.print_exc()
        return None


def get_ongoing_quiz_attempt_for_student(db: Session, user_id: str, quiz_id: str):
    """Lấy lần làm quiz đang diễn ra (chưa nộp)."""
    try:
        return (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.user_id == user_id,
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.status == "in_progress",
            )
            .order_by(QuizAttempt.started_at.desc())
            .first()
        )
    except Exception as e:
        print("❌ [get_ongoing_quiz_attempt_for_student] Lỗi:", e)
        traceback.print_exc()
        return None
