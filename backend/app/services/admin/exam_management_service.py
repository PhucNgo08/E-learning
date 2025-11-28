"""
==========================================================
🧠 SERVICE — Exam Management (v11.0 PRO MAX 2025)
Tối ưu hóa toàn diện:
- Validate mạnh (title / thời gian / logic)
- Check course tồn tại & teacher sở hữu khóa
- Fix lỗi crash từ router (ValueError / None / "")
- Chống tạo kỳ thi trùng
- Check timezone chuẩn Asia/Ho_Chi_Minh
- Tự động cập nhật total_questions sau import
==========================================================
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import uuid
import pytz

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt


# ============================================================
# 📌 TIMEZONE HCM (chuẩn cho lịch thi)
# ============================================================
TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def to_utc(dt):
    """Convert datetime-local → UTC"""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
    return dt.astimezone(pytz.UTC)


# ============================================================
# 📌 1. Lấy danh sách bài thi
# ============================================================
def get_exams(db: Session, user_id: str, role: str):
    base = db.query(Quiz).filter(Quiz.quiz_type == "graded")

    # ADMIN
    if role == "admin":
        return base.order_by(Quiz.created_at.desc()).all()

    # TEACHER → bài thi thuộc khóa mình dạy
    if role == "teacher":
        return (
            base.join(Course, Quiz.course_id == Course.id)
            .filter(Course.teacher_id == user_id)
            .order_by(Quiz.created_at.desc())
            .all()
        )

    # STUDENT → bài thi có thể làm
    if role == "student":
        now = datetime.utcnow()
        return (
            base.join(Course, Quiz.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.enrollment_status.in_(
                    ["active", "approved", "completed"]
                ),
                Quiz.is_approved == True,
                Quiz.status == "published",
                Quiz.available_from <= now,
                Quiz.available_to >= now,
            )
            .order_by(Quiz.available_from.asc())
            .all()
        )
    return []


# ============================================================
# 📌 2. Validate đầu vào
# ============================================================
def validate_exam_inputs(
    title, total_questions, time_limit, max_attempts,
    passing_score, available_from, available_to
):

    if not title or len(title.strip()) < 3:
        raise ValueError("Tiêu đề kỳ thi quá ngắn.")

    if total_questions <= 0:
        raise ValueError("Số câu hỏi phải > 0.")

    if time_limit <= 0:
        raise ValueError("Thời gian phải > 0.")

    if max_attempts <= 0:
        raise ValueError("Số lần làm phải >= 1.")

    if not (0 <= passing_score <= 100):
        raise ValueError("Điểm qua môn phải trong 0–100.")

    if available_from and available_to:
        if available_to <= available_from:
            raise ValueError("Thời gian đóng phải lớn hơn thời gian mở.")


# ============================================================
# 📌 3. Check giáo viên sở hữu khóa học/bài thi
# ============================================================
def is_teacher_owner(db: Session, teacher_id: str, exam_id: str) -> bool:
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(
            Quiz.id == exam_id,
            Course.teacher_id == teacher_id
        )
        .first()
        is not None
    )


# ============================================================
# 📌 4. Check title duplicate
# ============================================================
def exam_title_exists(db: Session, title: str, course_id: str):
    return (
        db.query(Quiz)
        .filter(
            Quiz.course_id == course_id,
            Quiz.title == title.strip(),
            Quiz.quiz_type == "graded",
        )
        .first()
        is not None
    )


# ============================================================
# 📌 5. Tạo bài thi
# ============================================================
def create_exam(
    db: Session, user_id: str, role: str,
    title: str, description: str, course_id: str,
    total_questions: int, time_limit: int,
    max_attempts: int, passing_score: float,
    available_from, available_to
):

    # 1) Check course tồn tại
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Khóa học không tồn tại.")

    # 2) Teacher chỉ được tạo bài thi trong khóa mình
    if role == "teacher" and course.teacher_id != user_id:
        raise PermissionError("Bạn không thể tạo bài thi cho khóa này.")

    # 3) Validate input
    validate_exam_inputs(
        title, total_questions, time_limit,
        max_attempts, passing_score,
        available_from, available_to
    )

    # 4) Check duplicate title
    if exam_title_exists(db, title, course_id):
        raise ValueError("Tên kỳ thi đã tồn tại trong khóa học này.")

    try:
        exam = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description.strip() if description else None,
            course_id=course_id,
            quiz_type="graded",
            total_questions=total_questions,
            time_limit_minutes=time_limit,
            max_attempts=max_attempts,
            passing_score=passing_score,
            available_from=to_utc(available_from),
            available_to=to_utc(available_to),
            randomize_questions=True,
            randomize_options=True,
            show_correct_answers=False,
            status="pending",
            is_approved=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi tạo bài thi: {str(e)}")


# ============================================================
# 📌 6. Cập nhật bài thi
# ============================================================
def update_exam(
    db: Session, user_id: str, role: str, exam_id: str,
    title: str, description: str, total_questions: int,
    time_limit: int, max_attempts: int, passing_score: float,
    available_from, available_to
):

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    # Teacher chỉ sửa bài thi của mình
    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không thể sửa bài thi này.")

    validate_exam_inputs(
        title, total_questions, time_limit,
        max_attempts, passing_score,
        available_from, available_to
    )

    # Title trùng với bài thi khác trong cùng khóa
    if exam.title.strip() != title.strip():
        if exam_title_exists(db, title, exam.course_id):
            raise ValueError("Tiêu đề kỳ thi đã tồn tại.")

    try:
        exam.title = title.strip()
        exam.description = description.strip() if description else None
        exam.total_questions = total_questions
        exam.time_limit_minutes = time_limit
        exam.max_attempts = max_attempts
        exam.passing_score = passing_score
        exam.available_from = to_utc(available_from)
        exam.available_to = to_utc(available_to)

        # Reset lại trạng thái để Admin duyệt
        exam.status = "pending"
        exam.is_approved = False
        exam.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(exam)
        return exam

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi cập nhật bài thi: {str(e)}")


# ============================================================
# 📌 7. Xóa bài thi
# ============================================================
def delete_exam(db: Session, user_id: str, role: str, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không được xóa bài thi này.")

    try:
        # Xóa options trước
        db.query(QuestionOption).filter(
            QuestionOption.question_id.in_(
                db.query(Question.id).filter(Question.quiz_id == exam_id)
            )
        ).delete(synchronize_session=False)

        # Xóa questions
        db.query(Question).filter(
            Question.quiz_id == exam_id
        ).delete(synchronize_session=False)

        db.delete(exam)
        db.commit()
        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi xóa bài thi: {str(e)}")


# ============================================================
# 📌 8. Duyệt bài thi
# ============================================================
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


# ============================================================
# 📌 9. Từ chối bài thi
# ============================================================
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


# ============================================================
# 📌 10. Đếm số lần làm bài
# ============================================================
def get_student_attempt_count(db: Session, user_id: str, exam_id: str):
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id == exam_id
        )
        .count()
    )


# ============================================================
# 📌 11. Auto cập nhật số câu hỏi sau import
# ============================================================
def update_question_count(db: Session, exam_id: str):
    """Đếm số câu hỏi thực tế sau import & update vào quiz."""
    count = db.query(Question).filter(Question.quiz_id == exam_id).count()

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if exam:
        exam.total_questions = count
        exam.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(exam)

    return count
# ============================================================
# 📌 NEW — 12. Lấy 1 câu hỏi theo ID
# ============================================================
def get_question(db: Session, question_id: str):
    return db.query(Question).filter(Question.id == question_id).first()


# ============================================================
# 📌 NEW — 13. Lấy danh sách câu hỏi theo bài thi
# ============================================================
def get_questions_by_exam(db: Session, exam_id: str):
    return db.query(Question).filter(Question.quiz_id == exam_id).all()


# ============================================================
# 📌 NEW — 14. Thêm câu hỏi thủ công
# ============================================================
def create_question(
    db: Session,
    exam_id: str,
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct: str
):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if correct.upper() not in ["A", "B", "C", "D"]:
        raise ValueError("Đáp án phải là A / B / C / D.")

    try:
        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=exam_id,
            question_text=question_text.strip(),
            difficulty_level=exam.difficulty_level
        )
        db.add(new_q)
        db.flush()

        options = {
            "A": option_a,
            "B": option_b,
            "C": option_c,
            "D": option_d
        }

        for letter, text in options.items():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=text.strip(),
                is_correct=(letter == correct.upper())
            ))

        db.commit()

        # Cập nhật tổng số câu
        update_question_count(db, exam_id)

        return new_q

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi thêm câu hỏi: {str(e)}")


# ============================================================
# 📌 NEW — 15. Sửa câu hỏi
# ============================================================
def update_question(
    db: Session,
    question_id: str,
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct: str
):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise ValueError("Không tìm thấy câu hỏi.")

    if correct.upper() not in ["A", "B", "C", "D"]:
        raise ValueError("Đáp án phải là A / B / C / D.")

    try:
        q.question_text = question_text.strip()

        # Xóa option cũ
        db.query(QuestionOption).filter(
            QuestionOption.question_id == question_id
        ).delete()

        # Thêm option mới
        options = {
            "A": option_a,
            "B": option_b,
            "C": option_c,
            "D": option_d
        }

        for letter, text in options.items():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=question_id,
                option_text=text.strip(),
                is_correct=(letter == correct.upper())
            ))

        db.commit()
        return q

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi sửa câu hỏi: {str(e)}")


# ============================================================
# 📌 NEW — 16. Xóa câu hỏi
# ============================================================
def delete_question(db: Session, question_id: str):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise ValueError("Không tìm thấy câu hỏi.")

    try:
        exam_id = q.quiz_id

        # Xóa options
        db.query(QuestionOption).filter(
            QuestionOption.question_id == question_id
        ).delete()

        # Xóa câu hỏi
        db.delete(q)
        db.commit()

        # Cập nhật total_questions
        update_question_count(db, exam_id)

        return True

    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi xóa câu hỏi: {str(e)}")
