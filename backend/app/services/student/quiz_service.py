from sqlalchemy.orm import Session, joinedload
from app.database.connection import SessionLocal
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
import uuid
from datetime import datetime


# =====================================================
# 📘 LẤY DANH SÁCH QUIZ (CHO SINH VIÊN)
# =====================================================
def get_all_quizzes_for_student():
    """
    Lấy danh sách toàn bộ quiz đang hoạt động (theo thời gian cho phép).
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        quizzes = (
            db.query(Quiz)
            .filter(
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now)
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
        return quizzes
    finally:
        db.close()


# =====================================================
# 📗 LẤY QUIZ THEO KHÓA HỌC
# =====================================================
def get_quizzes_by_course(course_id: str):
    """
    Lấy danh sách quiz thuộc về một khóa học cụ thể.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        quizzes = (
            db.query(Quiz)
            .filter(
                Quiz.course_id == course_id,
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now)
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )
        return quizzes
    finally:
        db.close()


# =====================================================
# 🧩 LẤY QUIZ + DANH SÁCH CÂU HỎI + LỰA CHỌN
# =====================================================
def get_quiz_with_questions(quiz_id: str):
    """
    Lấy thông tin quiz + danh sách câu hỏi (và các lựa chọn).
    """
    db: Session = SessionLocal()
    try:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return None

        questions = (
            db.query(Question)
            .filter(Question.quiz_id == quiz_id)
            .order_by(Question.question_order)
            .all()
        )

        for q in questions:
            q.options = (
                db.query(QuestionOption)
                .filter(QuestionOption.question_id == q.id)
                .order_by(QuestionOption.option_order)
                .all()
            )

        return {"quiz": quiz, "questions": questions}
    finally:
        db.close()


# =====================================================
# 📝 NỘP BÀI QUIZ (TẠO ATTEMPT)
# =====================================================
def submit_quiz(quiz_id: str, form_data, user_id: str):
    """
    Xử lý khi sinh viên nộp bài quiz:
    - Ghi vào quiz_attempt
    - Ghi từng câu trả lời vào attempt_answer
    - Tính điểm tự động
    """
    db: Session = SessionLocal()
    try:
        if not user_id:
            raise ValueError("❌ User ID không được để trống khi nộp bài quiz")

        # 🆕 Tạo bản ghi attempt
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

        # 🧮 Tính điểm
        correct = 0
        total = 0

        for key, value in form_data.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                selected_id = value

                # Kiểm tra đúng/sai
                option = db.query(QuestionOption).filter(QuestionOption.id == selected_id).first()
                is_correct = bool(option and option.is_correct)
                total += 1
                if is_correct:
                    correct += 1

                # Lưu câu trả lời
                db.add(AttemptAnswer(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_id,
                    question_id=question_id,
                    selected_option_id=selected_id,
                    is_correct=is_correct,
                    points_earned=1 if is_correct else 0
                ))

        # 🧾 Cập nhật điểm tổng
        score = round((correct / max(total, 1)) * 100, 2)
        attempt.score = score
        attempt.correct_answers = correct
        attempt.total_questions = total

        db.commit()
        return {"attempt_id": attempt_id, "score": score}

    finally:
        db.close()


# =====================================================
# 🎯 XEM KẾT QUẢ QUIZ (ATTEMPT)
# =====================================================
def get_quiz_result(attempt_id: str):
    """
    Lấy kết quả của một attempt (bao gồm danh sách câu trả lời).
    """
    db: Session = SessionLocal()
    try:
        attempt = (
            db.query(QuizAttempt)
            .options(
                joinedload(QuizAttempt.quiz),       # ✅ Load quiz để tránh DetachedInstanceError
                joinedload(QuizAttempt.answers)
            )
            .filter(QuizAttempt.id == attempt_id)
            .first()
        )

        if not attempt:
            return None

        answers = (
            db.query(AttemptAnswer)
            .options(joinedload(AttemptAnswer.question))
            .filter(AttemptAnswer.attempt_id == attempt_id)
            .all()
        )

        return {"attempt": attempt, "answers": answers}
    finally:
        db.close()


# =====================================================
# 🕓 LỊCH SỬ QUIZ THEO SINH VIÊN
# =====================================================
def get_quiz_history_for_student(user_id: str):
    """
    Lấy toàn bộ lịch sử làm bài của một sinh viên.
    Tránh DetachedInstanceError bằng joinedload(QuizAttempt.quiz).
    """
    db: Session = SessionLocal()
    try:
        history = (
            db.query(QuizAttempt)
            .options(joinedload(QuizAttempt.quiz))  # ✅ load trước quan hệ quiz
            .filter(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.started_at.desc())
            .all()
        )
        return history
    finally:
        db.close()
