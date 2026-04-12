from datetime import datetime
import uuid

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.quiz import Quiz
from app.models.quiz_attempt import QuizAttempt
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.rbac import Role
from app.models.course_enrollment import CourseEnrollment


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


# ====================================================
# 📋 Lấy danh sách bài tập theo giáo viên
# ====================================================
def get_assignments_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Assignment)
        .options(joinedload(Assignment.course), joinedload(Assignment.module))
        .filter(Assignment.teacher_id == teacher_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )


def get_assignment_owned(db: Session, assignment_id: str, teacher_id: str):
    return (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == teacher_id,
        )
        .first()
    )


# ====================================================
# ➕ Tạo bài tập mới
# ====================================================
def create_assignment(
    db: Session,
    course_id: str,
    module_id: str | None,
    teacher_id: str,
    title: str,
    description: str | None,
    due_date: datetime,
    allowed_file_types: str = "pdf,docx,zip",
    max_files: int = 3,
    max_file_size_mb: int = 50,
):
    title = _clean_text(title)
    description = _clean_text(description)

    if not title:
        raise ValueError("Tiêu đề bài tập không được để trống.")
    if not course_id:
        raise ValueError("Khóa học không hợp lệ.")
    if due_date is None:
        raise ValueError("Hạn nộp không được để trống.")

    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == teacher_id)
        .first()
    )
    if not course:
        raise ValueError("Khóa học không hợp lệ hoặc không thuộc giáo viên.")

    if module_id:
        module = db.query(Module).filter(Module.id == module_id).first()
        if not module:
            raise ValueError("Module không tồn tại.")
        if module.course_id != course_id:
            raise ValueError("Module không thuộc khóa học được chọn.")

    now = datetime.utcnow()

    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        course_id=course_id,
        module_id=module_id,
        teacher_id=teacher_id,
        title=title,
        description=description,
        due_date=due_date,
        allowed_file_types=allowed_file_types,
        max_files=max_files,
        max_file_size_mb=max_file_size_mb,
        start_date=now,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment
    except SQLAlchemyError:
        db.rollback()
        raise


# ====================================================
# ✏️ Cập nhật bài tập
# ====================================================
def update_assignment_by_teacher(
    db: Session,
    assignment_id: str,
    teacher_id: str,
    title: str,
    description: str | None,
    due_date: datetime | None = None,
):
    assignment = get_assignment_owned(db, assignment_id, teacher_id)
    if not assignment:
        return None

    title = _clean_text(title)
    description = _clean_text(description)

    if not title:
        raise ValueError("Tiêu đề bài tập không được để trống.")

    assignment.title = title
    assignment.description = description
    if due_date is not None:
        assignment.due_date = due_date
    assignment.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except SQLAlchemyError:
        db.rollback()
        raise


# ====================================================
# 🗑️ Xóa bài tập
# ====================================================
def delete_assignment_by_teacher(db: Session, assignment_id: str, teacher_id: str):
    assignment = get_assignment_owned(db, assignment_id, teacher_id)
    if not assignment:
        return False

    try:
        submission_ids = [
            row[0]
            for row in db.query(AssignmentSubmission.id)
            .filter(AssignmentSubmission.assignment_id == assignment_id)
            .all()
        ]

        if submission_ids:
            db.query(AssignmentFile).filter(
                AssignmentFile.submission_id.in_(submission_ids)
            ).delete(synchronize_session=False)

        db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id
        ).delete(synchronize_session=False)

        db.delete(assignment)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise


# ====================================================
# 📄 Danh sách bài nộp theo bài tập
# ====================================================
def get_submissions_by_assignment(db: Session, assignment_id: str):
    return (
        db.query(AssignmentSubmission)
        .options(joinedload(AssignmentSubmission.student))
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.desc())
        .all()
    )


# ====================================================
# 🧮 Chấm bài nộp
# ====================================================
def grade_submission(
    db: Session,
    submission_id: str,
    grade: float,
    feedback: str,
    teacher_id: str,
):
    submission = db.query(AssignmentSubmission).filter_by(id=submission_id).first()
    if not submission:
        return None

    assignment = db.query(Assignment).filter_by(id=submission.assignment_id).first()
    if not assignment or assignment.teacher_id != teacher_id:
        raise PermissionError("Bạn không có quyền chấm bài này.")

    submission.grade = grade
    submission.feedback = _clean_text(feedback)
    submission.status = "graded"
    submission.graded_by = teacher_id
    submission.graded_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(submission)
        return submission
    except SQLAlchemyError:
        db.rollback()
        raise


# ====================================================
# 📦 Lấy file đính kèm bài nộp
# ====================================================
def get_submission_files(db: Session, submission_id: str):
    return (
        db.query(AssignmentFile)
        .filter(AssignmentFile.submission_id == submission_id)
        .all()
    )


# ====================================================
# 📊 Lấy dữ liệu export Excel
# ====================================================
def get_submission_export_rows(db: Session, assignment_id: str):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    deadline = assignment.due_date if assignment else None

    file_count_sq = (
        db.query(
            AssignmentFile.submission_id.label("sid"),
            func.count(AssignmentFile.id).label("file_count"),
        )
        .group_by(AssignmentFile.submission_id)
        .subquery()
    )

    q = (
        db.query(
            AssignmentSubmission.id,
            AssignmentSubmission.submission_time,
            AssignmentSubmission.status,
            AssignmentSubmission.grade,
            AssignmentSubmission.feedback,
            StudentProfile.mssv.label("mssv"),
            UserProfile.full_name.label("full_name"),
            User.email,
            func.coalesce(file_count_sq.c.file_count, 0).label("file_count"),
        )
        .join(User, User.id == AssignmentSubmission.student_id, isouter=True)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .join(file_count_sq, file_count_sq.c.sid == AssignmentSubmission.id, isouter=True)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.asc())
    )

    rows = []
    for r in q.all():
        is_late = bool(deadline and r.submission_time and r.submission_time > deadline)

        rows.append(
            {
                "submission_id": r.id,
                "submission_time": r.submission_time,
                "status": r.status,
                "grade": r.grade,
                "feedback": r.feedback,
                "mssv": r.mssv,
                "full_name": r.full_name,
                "email": r.email,
                "file_count": r.file_count,
                "is_late": is_late,
            }
        )

    return rows


# ====================================================
# 🎯 Tiến độ học viên theo khóa học
# ====================================================
def get_student_progress_by_course(db: Session, course_id: str):
    students = (
        db.query(User)
        .join(CourseEnrollment, CourseEnrollment.user_id == User.id)
        .join(User.roles)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.enrollment_status.in_(["active", "approved", "completed"]),
            Role.role_code == "student",
        )
        .distinct()
        .all()
    )

    total_lessons = (
        db.query(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.course_id == course_id)
        .count()
    )

    total_assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .count()
    )

    total_quizzes = (
        db.query(Quiz)
        .filter(Quiz.course_id == course_id)
        .count()
    )

    progress_list = []

    for stu in students:
        lessons_completed = (
            db.query(LessonProgress)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .filter(
                LessonProgress.user_id == stu.id,
                LessonProgress.progress_status == "completed",
                Module.course_id == course_id,
            )
            .count()
        )

        assignments_submitted = (
            db.query(AssignmentSubmission)
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(
                Assignment.course_id == course_id,
                AssignmentSubmission.student_id == stu.id,
            )
            .count()
        )

        quiz_done = (
            db.query(QuizAttempt)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .filter(
                QuizAttempt.user_id == stu.id,
                QuizAttempt.status == "submitted",
                Quiz.course_id == course_id,
            )
            .count()
        )

        lesson_ratio = (lessons_completed / total_lessons) if total_lessons else 0
        assignment_ratio = (assignments_submitted / total_assignments) if total_assignments else 0
        quiz_ratio = (quiz_done / total_quizzes) if total_quizzes else 0

        overall_progress = round(
            (lesson_ratio * 0.5 + assignment_ratio * 0.3 + quiz_ratio * 0.2) * 100,
            1,
        )

        progress_list.append(
            {
                "student": stu,
                "lessons_completed": lessons_completed,
                "assignments_submitted": assignments_submitted,
                "quiz_done": quiz_done,
                "overall_progress": overall_progress,
            }
        )

    return progress_list