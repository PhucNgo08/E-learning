from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime
import uuid

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
from app.models.lesson_progress import LessonProgress
from app.models.quiz_attempt import QuizAttempt


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


# ====================================================
# ➕ Tạo bài tập mới
# ====================================================
def create_assignment(
    db: Session,
    course_id: str,
    module_id: str,
    teacher_id: str,
    title: str,
    description: str,
    due_date: datetime,
    allowed_file_types: str = "pdf,docx,zip",
    max_files: int = 3,
    max_file_size_mb: int = 50,
):
    try:
        # 1. Kiểm tra khóa học thuộc giáo viên
        course = (
            db.query(Course)
            .filter(Course.id == course_id, Course.teacher_id == teacher_id)
            .first()
        )
        if not course:
            raise ValueError("Khóa học không hợp lệ hoặc không thuộc giáo viên.")

        # 2. Kiểm tra module
        if module_id:
            module = db.query(Module).filter(Module.id == module_id).first()
            if not module:
                raise ValueError("Module không tồn tại.")
            if module.course_id != course_id:
                raise ValueError("Module không thuộc khóa học được chọn.")

        # 3. Tạo Assignment
        new_assignment = Assignment(
            id=str(uuid.uuid4()),
            course_id=course_id,
            module_id=module_id,
            teacher_id=teacher_id,
            title=title.strip(),
            description=description.strip() if description else None,
            due_date=due_date,
            allowed_file_types=allowed_file_types,
            max_files=max_files,
            max_file_size_mb=max_file_size_mb,
            start_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment

    except Exception as e:
        db.rollback()
        raise ValueError(f"Lỗi khi tạo bài tập: {str(e)}")


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
    db: Session, submission_id: str, grade: float, feedback: str, teacher_id: str
):
    submission = db.query(AssignmentSubmission).filter_by(id=submission_id).first()
    if not submission:
        return None

    assignment = db.query(Assignment).filter_by(id=submission.assignment_id).first()

    if not assignment or assignment.teacher_id != teacher_id:
        raise PermissionError("Bạn không có quyền chấm bài này.")

    submission.grade = grade
    submission.feedback = feedback
    submission.status = "graded"
    submission.graded_by = teacher_id
    submission.graded_at = datetime.now()

    db.commit()
    db.refresh(submission)
    return submission


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
            User.mssv,
            User.full_name,
            User.email,
            func.coalesce(file_count_sq.c.file_count, 0).label("file_count"),
        )
        .join(User, User.id == AssignmentSubmission.student_id, isouter=True)
        .join(file_count_sq, file_count_sq.c.sid == AssignmentSubmission.id, isouter=True)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.asc())
    )

    rows = []
    for r in q.all():
        is_late = False
        if deadline and r.submission_time:
            is_late = r.submission_time > deadline

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
# 🎯 NEW – Tính tiến độ học viên theo khóa học
# ====================================================
def get_student_progress_by_course(db: Session, course_id: str):
    """
    Trả về list chứa data tiến độ học viên trong khóa học:
    - lessons_completed
    - assignments_submitted
    - quiz_done
    - overall_progress (%)
    """

    # ======= Lấy danh sách sinh viên đang học khóa
    students = (
        db.query(User)
        .join(Assignment, Assignment.course_id == course_id)
        .filter(User.role == "student")
        .distinct()
        .all()
    )

    progress_list = []

    for stu in students:

        # ---------------------------
        # 1. Tiến độ bài học
        # ---------------------------
        lessons_completed = (
            db.query(LessonProgress)
            .join(Module, Module.id == LessonProgress.lesson_id)
            .filter(
                LessonProgress.user_id == stu.id,
                LessonProgress.progress_status == "completed",
            )
            .count()
        )

        # ---------------------------
        # 2. Bài tập đã nộp
        # ---------------------------
        assignments_submitted = (
            db.query(AssignmentSubmission)
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(
                Assignment.course_id == course_id,
                AssignmentSubmission.student_id == stu.id,
            )
            .count()
        )

        # ---------------------------
        # 3. Quiz đã làm
        # ---------------------------
        quiz_done = (
            db.query(QuizAttempt)
            .filter(
                QuizAttempt.user_id == stu.id,
                QuizAttempt.status == "submitted",
            )
            .count()
        )

        # ---------------------------
        # 4. Tổng hợp phần trăm tiến độ
        # ---------------------------
        overall_progress = (
            lessons_completed * 0.5 + assignments_submitted * 0.3 + quiz_done * 0.2
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
