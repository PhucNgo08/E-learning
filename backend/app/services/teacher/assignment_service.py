from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
import uuid


# ====================================================
# 📋 Lấy danh sách bài tập theo giáo viên
# ====================================================
def get_assignments_by_teacher(db: Session, teacher_id: str):
    """
    Truy vấn tất cả bài tập do giáo viên tạo
    Trả về kèm thông tin khóa học và module (nếu có)
    """
    assignments = (
        db.query(Assignment)
        .filter(Assignment.teacher_id == teacher_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )

    # ✅ Gắn tên khóa học và module để hiển thị trong template
    for a in assignments:
        a.course = db.query(Course).filter(Course.id == a.course_id).first()
        a.module = db.query(Module).filter(Module.id == a.module_id).first() if a.module_id else None

    return assignments


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
    """
    Tạo mới bài tập (Assignment)
    Kiểm tra:
    - Khóa học (course_id) phải tồn tại và thuộc về giáo viên
    - Module (nếu có) phải thuộc khóa học đó
    """
    try:
        # ✅ Kiểm tra khóa học
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise ValueError("❌ Khóa học không tồn tại hoặc không hợp lệ.")

        # ✅ Kiểm tra module (nếu có)
        if module_id:
            module = db.query(Module).filter(Module.id == module_id).first()
            if not module:
                raise ValueError("❌ Module không tồn tại.")
            if module.course_id != course_id:
                raise ValueError("❌ Module không thuộc khóa học được chọn.")

        # ✅ Tạo bài tập
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
# 📄 Danh sách bài nộp theo Assignment
# ====================================================
def get_submissions_by_assignment(db: Session, assignment_id: str):
    """
    Lấy danh sách bài nộp kèm thông tin sinh viên (dạng object)
    Trả về list[AssignmentSubmission] với .student property gắn sẵn
    """
    submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.desc())
        .all()
    )

    # ✅ Gắn thêm thông tin sinh viên
    for s in submissions:
        s.student = db.query(User).filter(User.id == s.student_id).first()
    return submissions


# ====================================================
# 🧮 Chấm điểm bài nộp
# ====================================================
def grade_submission(
    db: Session, submission_id: str, grade: float, feedback: str, teacher_id: str
):
    """Chấm điểm bài nộp"""
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        return None

    submission.grade = grade
    submission.feedback = feedback
    submission.status = "graded"
    submission.graded_by = teacher_id
    submission.graded_at = datetime.now()

    db.commit()
    db.refresh(submission)
    return submission


# ====================================================
# 📦 Lấy file đính kèm của bài nộp
# ====================================================
def get_submission_files(db: Session, submission_id: str):
    """Lấy danh sách file đính kèm bài nộp"""
    return (
        db.query(AssignmentFile)
        .filter(AssignmentFile.submission_id == submission_id)
        .all()
    )


# ====================================================
# 📊 Dữ liệu Export Excel
# ====================================================
def get_submission_export_rows(db: Session, assignment_id: str):
    """
    Trả về list[dict] chứa dữ liệu cần export Excel:
    mssv, full_name, email, submission_time, status, grade, feedback, file_count
    """
    # Subquery đếm số file mỗi bài nộp
    file_count_sq = (
        db.query(
            AssignmentFile.submission_id.label("sid"),
            func.count(AssignmentFile.id).label("file_count")
        )
        .group_by(AssignmentFile.submission_id)
        .subquery()
    )

    # JOIN submissions + users + file_count
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
            func.coalesce(file_count_sq.c.file_count, 0).label("file_count")
        )
        .join(User, User.id == AssignmentSubmission.student_id, isouter=True)
        .join(file_count_sq, file_count_sq.c.sid == AssignmentSubmission.id, isouter=True)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.asc())
    )

    rows = []
    for r in q.all():
        rows.append({
            "submission_id": r.id,
            "submission_time": r.submission_time,
            "status": r.status,
            "grade": r.grade,
            "feedback": r.feedback,
            "mssv": r.mssv,
            "full_name": r.full_name,
            "email": r.email,
            "file_count": r.file_count,
        })
    return rows
