"""
==========================================================
📘 SERVICE: Student - Quiz (FULL 100% Production-Ready)
Xử lý quiz cho học viên: lấy quiz, làm bài, nộp bài, xem kết quả
==========================================================
"""

from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import uuid
import traceback

from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from app.models.lesson_progress import LessonProgress


# ======================================================
# 📗 LẤY DANH SÁCH QUIZ HOẠT ĐỘNG
# ======================================================
def get_all_quizzes_for_student(db: Session):
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
                Quiz.status == "published"
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
    try:
        now = datetime.utcnow()
        return (
            db.query(Quiz)
            .filter(
                Quiz.course_id == course_id,
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now),
                Quiz.status == "published"
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_quizzes_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# ======================================================
# 🧩 LẤY QUIZ + CÂU HỎI + OPTIONS
# ======================================================
def get_quiz_with_questions(db: Session, quiz_id: str):
    try:
        quiz = (
            db.query(Quiz)
            .options(joinedload(Quiz.questions).joinedload(Question.options))
            .filter(Quiz.id == quiz_id)
            .first()
        )

        if not quiz:
            return None

        # Random câu hỏi
        if quiz.randomize_questions:
            quiz.questions.sort(key=lambda x: uuid.uuid4())

        # Random đáp án
        if quiz.randomize_options:
            for q in quiz.questions:
                q.options.sort(key=lambda x: uuid.uuid4())

        return quiz

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
            raise ValueError("User ID không được để trống")

        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise ValueError("Quiz không tồn tại")

        # ===== CHECK MAX ATTEMPTS =====
        previous_attempts = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.quiz_id == quiz_id,
                    QuizAttempt.user_id == user_id)
            .count()
        )

        if quiz.max_attempts and previous_attempts >= quiz.max_attempts:
            return {"error": "Bạn đã đạt số lần làm bài tối đa."}

        attempt_number = previous_attempts + 1

        # ===== TẠO ATTEMPT =====
        attempt_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        submitted_at = datetime.utcnow()

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

        # ===== CHẤM BÀI =====
        correct = 0
        total = 0

        for key, value in form_data.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                selected_id = value

                option = db.query(QuestionOption).filter(
                    QuestionOption.id == selected_id
                ).first()

                is_correct = bool(option and option.is_correct)
                total += 1
                if is_correct:
                    correct += 1

                db.add(
                    AttemptAnswer(
                        id=str(uuid.uuid4()),
                        attempt_id=attempt_id,
                        question_id=question_id,
                        selected_option_id=selected_id,
                        is_correct=is_correct,
                        points_earned=1 if is_correct else 0,
                    )
                )

        score = round((correct / max(total, 1)) * 100, 2)

        # Tính thời gian
        time_spent = int((submitted_at - started_at).total_seconds())

        # ===== UPDATE ATTEMPT =====
        attempt.score = score
        attempt.correct_answers = correct
        attempt.total_questions = total
        attempt.time_spent_seconds = time_spent

        db.commit()
        db.refresh(attempt)

        # ===== CẬP NHẬT LESSON PROGRESS (nếu quiz gắn vào bài học) =====
        if quiz.lesson_id:
            lp = (
                db.query(LessonProgress)
                .filter(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id == quiz.lesson_id,
                )
                .first()
            )
            if lp:
                lp.progress_status = "completed"
                lp.completion_percentage = 100
                lp.completed_at = datetime.utcnow()
                db.commit()

        print(f"✅ [submit_quiz] User={user_id} Quiz={quiz_id} Score={score}%")
        return {"attempt_id": attempt_id, "score": score}

    except Exception as e:
        db.rollback()
        print("❌ [submit_quiz] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🎯 XEM CHI TIẾT KẾT QUẢ QUIZ
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
    except Exception as e:
        print("❌ [get_quiz_result] Lỗi:", e)
        traceback.print_exc()
        return None


# ======================================================
# 🕓 LỊCH SỬ LÀM QUIZ
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
    except Exception as e:
        print("❌ [get_quiz_history_for_student] Lỗi:", e)
        traceback.print_exc()
        return []


def get_quiz_history_for_student_by_course(db: Session, user_id: str, course_id: str):
    try:
        return (
            db.query(QuizAttempt)
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)
            .filter(QuizAttempt.user_id == user_id, Quiz.course_id == course_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_quiz_history_for_student_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


def get_quiz_attempt_count_for_student(db: Session, user_id: str, quiz_id: str):
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .count()
        )
    except Exception as e:
        traceback.print_exc()
        return 0


def has_student_attempted_quiz(db: Session, user_id: str, quiz_id: str):
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .first()
            is not None
        )
    except:
        return False


def get_highest_score_for_student_quiz(db: Session, user_id: str, quiz_id: str):
    try:
        high = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.score.desc())
            .first()
        )
        return high.score if high else 0
    except:
        return 0


def get_latest_quiz_attempt_for_student(db: Session, user_id: str, quiz_id: str):
    try:
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
            .order_by(QuizAttempt.started_at.desc())
            .first()
        )
    except:
        return None
