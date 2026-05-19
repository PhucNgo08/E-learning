import traceback
from sqlalchemy import or_

from datetime import datetime
import random
import uuid

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, or_

from app.models.quiz import Quiz
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz_attempt import QuizAttempt
from app.models.attempt_answer import AttemptAnswer
from app.models.user import User
from app.models.user_profile import UserProfile


VALID_ENROLLMENT_STATUSES = ["active", "approved", "completed"]
VALID_QUIZ_TYPES = ["practice", "graded"]
VALID_DIFFICULTY_LEVELS = ["easy", "medium", "hard", "beginner", "intermediate", "advanced"]
VALID_QUIZ_STATUSES = ["draft", "pending", "published", "rejected", "archived"]


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ============================================================
# Utility validation
# ============================================================
def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_quiz_inputs(
    title: str,
    quiz_type: str,
    difficulty_level: str,
    max_attempts: int,
    passing_score: float,
    total_questions: int,
    available_from: datetime = None,
    available_to: datetime = None,
):
    if not _clean_text(title):
        raise ValueError("Tiêu đề quiz không được để trống.")

    if quiz_type not in VALID_QUIZ_TYPES:
        raise ValueError("Loại quiz không hợp lệ.")

    if difficulty_level not in VALID_DIFFICULTY_LEVELS:
        raise ValueError("Độ khó quiz không hợp lệ.")

    if max_attempts is None or int(max_attempts) <= 0:
        raise ValueError("Số lần làm phải lớn hơn 0.")

    if total_questions is None or int(total_questions) <= 0:
        raise ValueError("Tổng số câu hỏi phải lớn hơn 0.")

    if passing_score is None or not (0 <= float(passing_score) <= 100):
        raise ValueError("Điểm đạt phải từ 0 đến 100.")

    if available_from and available_to and available_to <= available_from:
        raise ValueError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu.")


def validate_exam_inputs(
    title: str,
    total_questions: int,
    time_limit: int,
    max_attempts: int,
    passing_score: float,
    available_from,
    available_to,
):
    if not _clean_text(title):
        raise ValueError("Tiêu đề bài thi không được để trống.")

    if total_questions is None or int(total_questions) <= 0:
        raise ValueError("Số câu hỏi phải lớn hơn 0.")

    if time_limit is None or int(time_limit) <= 0:
        raise ValueError("Thời gian làm bài phải lớn hơn 0.")

    if max_attempts is None or int(max_attempts) <= 0:
        raise ValueError("Số lần làm tối thiểu phải >= 1.")

    if passing_score is None or not (0 <= float(passing_score) <= 100):
        raise ValueError("Điểm qua môn phải từ 0 đến 100.")

    if available_from and available_to and available_to <= available_from:
        raise ValueError("Thời gian đóng phải lớn hơn thời gian mở.")


# ===================================================================
# TEACHER SERVICE
# ===================================================================
def get_quizzes_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .order_by(Quiz.created_at.desc())
        .all()
    )


def get_quiz_by_id(db: Session, quiz_id: str, teacher_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .options(joinedload(Quiz.course))
        .first()
    )


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
    validate_quiz_inputs(
        title=title,
        quiz_type=quiz_type,
        difficulty_level=difficulty_level,
        max_attempts=max_attempts,
        passing_score=passing_score,
        total_questions=total_questions,
        available_from=available_from,
        available_to=available_to,
    )

    if status not in VALID_QUIZ_STATUSES:
        raise ValueError("Trạng thái quiz không hợp lệ.")

    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not course:
        raise PermissionError("Bạn không có quyền tạo quiz trong khóa học này.")

    try:
        quiz = Quiz(
            id=generate_uuid(),
            title=title.strip(),
            description=_clean_text(description),
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
    except Exception:
        db.rollback()
        raise


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
    validate_quiz_inputs(
        title=title,
        quiz_type=quiz_type,
        difficulty_level=difficulty_level,
        max_attempts=max_attempts,
        passing_score=passing_score,
        total_questions=total_questions,
        available_from=available_from,
        available_to=available_to,
    )

    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return None

    target_course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not target_course:
        raise PermissionError("Bạn không có quyền chuyển quiz sang khóa học này.")

    try:
        quiz.course_id = course_id
        quiz.title = title.strip()
        quiz.description = _clean_text(description)
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
    except Exception:
        db.rollback()
        raise


def delete_quiz(db: Session, teacher_id: str, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not quiz:
        return False

    try:
        db.query(QuestionOption).filter(
            QuestionOption.question_id.in_(
                db.query(Question.id).filter(Question.quiz_id == quiz_id)
            )
        ).delete(synchronize_session=False)

        db.query(Question).filter(Question.quiz_id == quiz_id).delete(synchronize_session=False)

        db.delete(quiz)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def get_quiz_detail(db: Session, teacher_id: str, quiz_id: str):
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Quiz.id == quiz_id, Course.teacher_id == teacher_id)
        .options(
            joinedload(Quiz.course),
            joinedload(Quiz.questions).joinedload(Question.options),
        )
        .first()
    )


def get_quiz_statistics(db: Session, teacher_id: str, quiz_id: str):
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
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
            UserProfile.full_name.label("full_name"),
            QuizAttempt.score,
            QuizAttempt.attempt_number,
            QuizAttempt.submitted_at,
        )
        .join(User, User.id == QuizAttempt.user_id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.status == "submitted",
        )
        .order_by(QuizAttempt.score.desc(), QuizAttempt.submitted_at.asc())
        .limit(5)
        .all()
    )

    return {
        "quiz": quiz,
        "stats": stats,
        "top_students": top_students,
    }


# ===================================================================
# EXAM SERVICE
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
            .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.enrollment_status.in_(VALID_ENROLLMENT_STATUSES),
                Quiz.is_approved == True,
                Quiz.status == "published",
                or_(Quiz.available_from.is_(None), Quiz.available_from <= now),
                or_(Quiz.available_to.is_(None), Quiz.available_to >= now),
            )
            .distinct()
            .order_by(Quiz.available_from.asc().nullsfirst(), Quiz.created_at.desc())
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
        if not course:
            raise ValueError("Không tìm thấy khóa học.")

    validate_exam_inputs(
        title, total_questions, time_limit, max_attempts, passing_score, available_from, available_to
    )

    try:
        exam = Quiz(
            id=generate_uuid(),
            title=title.strip(),
            description=_clean_text(description),
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
    except Exception:
        db.rollback()
        raise


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
        title, total_questions, time_limit, max_attempts, passing_score, available_from, available_to
    )

    try:
        exam.title = title.strip()
        exam.description = _clean_text(description)
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
    except Exception:
        db.rollback()
        raise


def delete_exam(db: Session, user_id: str, role: str, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    if role == "teacher" and not is_teacher_owner(db, user_id, exam_id):
        raise PermissionError("Bạn không có quyền xóa bài thi này.")

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
    except Exception:
        db.rollback()
        raise


def approve_exam(db: Session, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    try:
        exam.is_approved = True
        exam.status = "published"
        exam.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(exam)
        return exam
    except Exception:
        db.rollback()
        raise


def reject_exam(db: Session, exam_id: str):
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise ValueError("Không tìm thấy bài thi.")

    try:
        exam.is_approved = False
        exam.status = "rejected"
        exam.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(exam)
        return exam
    except Exception:
        db.rollback()
        raise


def get_student_attempt_count(db: Session, user_id: str, exam_id: str):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == exam_id)
        .count()
    )


# ===================================================================
# STUDENT SERVICE
# ===================================================================
def get_all_quizzes_for_student(db: Session):
    now = datetime.utcnow()
    return (
        db.query(Quiz)
        .filter(
            Quiz.quiz_type == "practice",
            Quiz.status == "published",
            or_(Quiz.available_from.is_(None), Quiz.available_from <= now),
            or_(Quiz.available_to.is_(None), Quiz.available_to >= now),
        )
        .order_by(Quiz.created_at.desc())
        .all()
    )


def get_quizzes_by_course(db: Session, course_id: str):
    try:
        now = datetime.utcnow()

        return (
            db.query(Quiz)
            .filter(
                Quiz.course_id == course_id,
                Quiz.quiz_type.in_(["practice", "graded"]),
                Quiz.status == "published",
                or_(Quiz.quiz_type != "graded", Quiz.is_approved == True),
                or_(Quiz.available_from.is_(None), Quiz.available_from <= now),
                or_(Quiz.available_to.is_(None), Quiz.available_to >= now),
            )
            .order_by(Quiz.created_at.desc())
            .all()
        )

    except Exception:
        traceback.print_exc()
        return []
    


def get_quiz_with_questions(db: Session, quiz_id: str):
    try:
        now = datetime.utcnow()

        quiz = (
            db.query(Quiz)
            .options(joinedload(Quiz.questions).joinedload(Question.options))
            .filter(
                Quiz.id == quiz_id,
                Quiz.quiz_type.in_(["practice", "graded"]),
                Quiz.status == "published",
                or_(Quiz.quiz_type != "graded", Quiz.is_approved == True),
                or_(Quiz.available_from.is_(None), Quiz.available_from <= now),
                or_(Quiz.available_to.is_(None), Quiz.available_to >= now),
            )
            .first()
        )

        if not quiz:
            return None

        quiz.questions = list(quiz.questions or [])

        if quiz.randomize_questions:
            random.shuffle(quiz.questions)

        if quiz.randomize_options:
            for q in quiz.questions:
                q.options = list(q.options or [])
                random.shuffle(q.options)

        return quiz

    except Exception:
        traceback.print_exc()
        return None

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


def submit_quiz(db: Session, quiz_id: str, form_data: dict, user_id: str):
    quiz = (
        db.query(Quiz)
        .options(joinedload(Quiz.questions).joinedload(Question.options))
        .filter(Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        return {"error": "Quiz không tồn tại"}

    now = datetime.utcnow()
    if quiz.status != "published":
        return {"error": "Quiz chưa được mở."}

    if quiz.quiz_type == "graded" and not bool(quiz.is_approved):
        return {"error": "Bài thi chưa được admin duyệt."}

    if quiz.available_from and now < quiz.available_from:
        return {"error": "Quiz chưa tới thời gian mở."}

    if quiz.available_to and now > quiz.available_to:
        return {"error": "Quiz đã hết thời gian làm."}

    if quiz.course_id:
        enrolled = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.user_id == user_id,
                CourseEnrollment.course_id == quiz.course_id,
                CourseEnrollment.enrollment_status.in_(VALID_ENROLLMENT_STATUSES),
            )
            .first()
        )
        if not enrolled:
            return {"error": "Bạn chưa đăng ký khóa học của quiz này."}

    if has_recent_attempt(db, user_id, quiz_id):
        return {"error": "Vui lòng đợi 1-2 giây trước khi nộp lại."}

    prev = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        .count()
    )
    if quiz.max_attempts and prev >= quiz.max_attempts:
        return {"error": "Bạn đã hết lượt làm bài."}

    try:
        started_raw = form_data.get("started_at")
        try:
            started_at = datetime.fromisoformat(started_raw) if started_raw else now
        except Exception:
            started_at = now
        submitted_at = datetime.utcnow()

        attempt_id = generate_uuid()
        attempt = QuizAttempt(
            id=attempt_id,
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_number=prev + 1,
            status="submitted",
            started_at=started_at,
            submitted_at=submitted_at,
        )
        db.add(attempt)
        db.flush()

        total_points = 0.0
        earned = 0.0
        correct = 0
        questions = list(quiz.questions or [])

        for question in questions:
            qid = str(question.id)
            selected = form_data.get(f"question_{qid}")
            total_points += float(question.points or 1)

            option = None
            if selected:
                option = (
                    db.query(QuestionOption)
                    .filter(
                        QuestionOption.id == selected,
                        QuestionOption.question_id == qid,
                    )
                    .first()
                )

            is_correct = bool(option and option.is_correct)
            if is_correct:
                earned += float(question.points or 1)
                correct += 1

            db.add(
                AttemptAnswer(
                    id=generate_uuid(),
                    attempt_id=attempt_id,
                    question_id=qid,
                    selected_option_id=selected if option else None,
                    is_correct=is_correct,
                    points_earned=float(question.points or 1) if is_correct else 0,
                )
            )

        score = round((earned / max(total_points, 1)) * 100, 2)
        attempt.score = score
        attempt.correct_answers = correct
        attempt.total_questions = len(questions)
        attempt.time_spent_seconds = max(0, int((submitted_at - started_at).total_seconds()))

        db.commit()
        db.refresh(attempt)
        return {"attempt_id": attempt_id, "score": score}
    except Exception as e:
        db.rollback()
        return {"error": f"Lỗi khi nộp bài: {e}"}

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


def get_latest_quiz_attempt_for_student(db: Session, user_id: str, quiz_id: str):
    return (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz_id)
        .order_by(QuizAttempt.started_at.desc())
        .first()
    )


def get_quiz_attempt_count_for_student(db: Session, user_id: str, quiz_id: str):
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.quiz_id == quiz_id,
        )
        .count()
    )


def get_all_quizzes_for_student_enrolled(db: Session, student_id: str):
    now = datetime.utcnow()
    return (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        .filter(
            CourseEnrollment.user_id == student_id,
            CourseEnrollment.enrollment_status.in_(VALID_ENROLLMENT_STATUSES),
            Quiz.quiz_type.in_(["practice", "graded"]),
            Quiz.status == "published",
            or_(Quiz.quiz_type != "graded", Quiz.is_approved == True),
            or_(Quiz.available_from.is_(None), Quiz.available_from <= now),
            or_(Quiz.available_to.is_(None), Quiz.available_to >= now),
        )
        .options(joinedload(Quiz.course))
        .distinct()
        .order_by(Quiz.created_at.desc())
        .all()
    )