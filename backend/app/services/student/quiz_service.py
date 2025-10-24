from sqlalchemy.orm import Session
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
    Trả về toàn bộ quiz mà sinh viên có thể thấy.
    (Không dùng cột status vì bảng quizzes không có)
    Có thể mở rộng để lọc theo available_from / available_to nếu cần.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        # Chỉ lấy quiz đang trong thời gian cho phép hoặc không giới hạn
        quizzes = (
            db.query(Quiz)
            .filter(
                (Quiz.available_from == None) | (Quiz.available_from <= now),
                (Quiz.available_to == None) | (Quiz.available_to >= now)
            )
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
    Lấy danh sách quiz thuộc một khóa học cụ thể.
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
            .all()
        )
        return quizzes
    finally:
        db.close()

# =====================================================
# 🧩 LẤY CHI TIẾT QUIZ + DANH SÁCH CÂU HỎI
# =====================================================
def get_quiz_with_questions(quiz_id: str):
    """
    Lấy quiz theo ID và danh sách các câu hỏi (cùng các lựa chọn).
    """
    db: Session = SessionLocal()
    try:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            return None

        # Lấy danh sách câu hỏi
        questions = (
            db.query(Question)
            .filter(Question.quiz_id == quiz_id)
            .order_by(Question.question_order)
            .all()
        )

        # Với mỗi câu hỏi, lấy các lựa chọn (option)
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
# 📝 NỘP BÀI QUIZ (TẠO QUIZ ATTEMPT)
# =====================================================
def submit_quiz(quiz_id: str, form_data):
    """
    Xử lý khi sinh viên nộp bài làm quiz:
    - Tạo quiz_attempt
    - Lưu từng câu trả lời (AttemptAnswer)
    - Tính điểm dựa vào số câu đúng
    """
    db: Session = SessionLocal()
    try:
        # Tạo attempt mới
        attempt_id = str(uuid.uuid4())
        attempt = QuizAttempt(
            id=attempt_id,
            quiz_id=quiz_id,
            user_id=None,  # TODO: Lấy user_id từ session đăng nhập nếu có
            status="submitted",
            started_at=datetime.utcnow(),
            submitted_at=datetime.utcnow(),
        )
        db.add(attempt)
        db.flush()

        # Duyệt form để tính điểm
        correct = 0
        total = 0

        for key, value in form_data.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                selected_id = value

                # Kiểm tra đáp án đúng/sai
                option = db.query(QuestionOption).filter(QuestionOption.id == selected_id).first()
                is_correct = bool(option and option.is_correct)
                total += 1
                if is_correct:
                    correct += 1

                # Ghi nhận vào bảng attempt_answer
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

        # Tính điểm phần trăm
        score = round((correct / max(total, 1)) * 100, 2)
        attempt.score = score
        attempt.correct_answers = correct
        attempt.total_questions = total

        db.commit()
        return {"attempt_id": attempt_id, "score": score}
    finally:
        db.close()

# =====================================================
# 🎯 XEM KẾT QUẢ QUIZ
# =====================================================
def get_quiz_result(attempt_id: str):
    """
    Lấy kết quả của một attempt (kết quả làm bài cụ thể).
    """
    db: Session = SessionLocal()
    try:
        attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
        answers = db.query(AttemptAnswer).filter(AttemptAnswer.attempt_id == attempt_id).all()
        return {"attempt": attempt, "answers": answers}
    finally:
        db.close()

# =====================================================
# 🕓 LỊCH SỬ LÀM QUIZ
# =====================================================
def get_quiz_history_for_student():
    """
    Trả về toàn bộ lịch sử làm bài quiz của sinh viên.
    """
    db: Session = SessionLocal()
    try:
        history = db.query(QuizAttempt).order_by(QuizAttempt.started_at.desc()).all()
        return history
    finally:
        db.close()
