from datetime import datetime
import uuid
from typing import Optional

import pytz
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt


TZ = pytz.timezone("Asia/Ho_Chi_Minh")
ACTIVE_COURSE_ENROLLMENT_STATUSES = {"active", "approved", "completed"}


def to_utc(dt):
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
    return dt.astimezone(pytz.UTC)


def _format_option(letter: str, text: str) -> str:
    letter = (letter or "").strip().upper()
    text = (text or "").strip()
    if letter in ["A", "B", "C", "D"]:
        return f"{letter}. {text}"
    return text


def get_exam_by_id(db: Session, exam_id: str) -> Optional[Quiz]:
    return db.query(Quiz).filter(Quiz.id == exam_id).first()


def get_course_by_id(db: Session, course_id: str) -> Optional[Course]:
    return db.query(Course).filter(Course.id == course_id).first()


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
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.enrollment_status.in_(ACTIVE_COURSE_ENROLLMENT_STATUSES),
                Quiz.is_approved == True,
                Quiz.status == "published",
                Quiz.available_from <= now,
                Quiz.available_to >= now,
            )
            .order_by(Quiz.available_from.asc())
            .all()
        )

    return []


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
    if available_from and available_to and available_to <= available_from:
        raise ValueError("Thời gian đóng phải lớn hơn thời gian mở.")


def is_teacher_owner(db: Session, teacher_id: str, exam_id: str) -> bool:
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == exam_id, Course.teacher_id == teacher_id)
        .first()
        is not None
    )


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


def create_exam(
    db: Session, user_id: str, role: str,
    title: str, description: str, course_id: str,
    total_questions: int, time_limit: int,
    max_attempts: int, passing_score: float,
    available_from, available_to
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise ValueError("Khóa học không tồn tại.")

    if role == "teacher" and course.teacher_id != user_id:
        raise PermissionError("Bạn không thể tạo bài thi cho khóa này.")

    validate_exam_inputs(
        title, total_questions, time_limit,
        max_attempts, passing_score,
        available_from, available_to
    )

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


def update_exam(
    db: Session, user_id: str, role: str, exam_id: str,
    title: str, description: str, total_questions: int,
    time_limit: int, max_attempts: int, passing_score: float,
    available_from, available_to
):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không thể sửa bài thi này.")

    validate_exam_inputs(
        title, total_questions, time_limit,
        max_attempts, passing_score,
        available_from, available_to
    )

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

        exam.status = "pending"
        exam.is_approved = False
        exam.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(exam)
        return exam
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi cập nhật bài thi: {str(e)}")


def delete_exam(db: Session, user_id: str, role: str, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không được xóa bài thi này.")

    try:
        db.query(QuestionOption).filter(
            QuestionOption.question_id.in_(
                db.query(Question.id).filter(Question.quiz_id == exam_id)
            )
        ).delete(synchronize_session=False)

        db.query(Question).filter(Question.quiz_id == exam_id).delete(synchronize_session=False)
        db.delete(exam)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi xóa bài thi: {str(e)}")


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


def update_question_count(db: Session, exam_id: str, new_total: int | None = None, commit: bool = True):
    if new_total is None:
        new_total = db.query(Question).filter(Question.quiz_id == exam_id).count()

    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if exam:
        exam.total_questions = int(new_total or 0)
        exam.updated_at = datetime.utcnow()
        if commit:
            db.commit()
            db.refresh(exam)
        else:
            db.flush()

    return int(new_total or 0)


def get_question(db: Session, question_id: str):
    return db.query(Question).filter(Question.id == question_id).first()


def get_questions_by_exam(db: Session, exam_id: str):
    return db.query(Question).filter(Question.quiz_id == exam_id).all()


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

    correct = (correct or "").strip().upper()
    if correct not in ["A", "B", "C", "D"]:
        raise ValueError("Đáp án phải là A / B / C / D.")

    try:
        new_q = Question(
            id=str(uuid.uuid4()),
            quiz_id=exam_id,
            question_text=(question_text or "").strip(),
            difficulty_level=exam.difficulty_level
        )
        db.add(new_q)
        db.flush()

        options = {"A": option_a, "B": option_b, "C": option_c, "D": option_d}
        for letter, text in options.items():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=new_q.id,
                option_text=_format_option(letter, text),
                is_correct=(letter == correct)
            ))

        db.commit()
        update_question_count(db, exam_id)
        return new_q
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi thêm câu hỏi: {str(e)}")


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

    correct = (correct or "").strip().upper()
    if correct not in ["A", "B", "C", "D"]:
        raise ValueError("Đáp án phải là A / B / C / D.")

    try:
        q.question_text = (question_text or "").strip()

        db.query(QuestionOption).filter(
            QuestionOption.question_id == question_id
        ).delete(synchronize_session=False)

        options = {"A": option_a, "B": option_b, "C": option_c, "D": option_d}
        for letter, text in options.items():
            db.add(QuestionOption(
                id=str(uuid.uuid4()),
                question_id=question_id,
                option_text=_format_option(letter, text),
                is_correct=(letter == correct)
            ))

        db.commit()
        update_question_count(db, q.quiz_id)
        return q
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi sửa câu hỏi: {str(e)}")


def delete_question(db: Session, question_id: str):
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        raise ValueError("Không tìm thấy câu hỏi.")

    try:
        exam_id = q.quiz_id
        db.query(QuestionOption).filter(
            QuestionOption.question_id == question_id
        ).delete(synchronize_session=False)

        db.delete(q)
        db.commit()
        update_question_count(db, exam_id)
        return True
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Lỗi xóa câu hỏi: {str(e)}")