"""
📘 Assignment Service (Admin)
CRUD + Thống kê + Xuất Excel cho bài tập.
"""

from datetime import datetime
import uuid

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.module import Module
from app.models.rbac import Role
from app.models.user import User
from app.models.user_profile import UserProfile


def _validate_assignment_payload(
    db: Session,
    title: str,
    course_id: str,
    module_id: str | None = None,
    teacher_id: str | None = None,
):
    title = (title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Tiêu đề bài tập không được để trống.")

    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=400, detail="Khóa học không tồn tại.")

    if module_id:
        module = db.query(Module).filter(Module.id == module_id).first()
        if not module:
            raise HTTPException(status_code=400, detail="Module không tồn tại.")
        if module.course_id != course_id:
            raise HTTPException(status_code=400, detail="Module không thuộc khóa học đã chọn.")

    if teacher_id:
        teacher = (
            db.query(User)
            .join(User.roles)
            .filter(
                User.id == teacher_id,
                Role.role_code.in_(["teacher", "admin"]),
            )
            .first()
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="Giảng viên phụ trách không hợp lệ.")

    return title, course


# =====================================================
# 1) Danh sách & chi tiết
# =====================================================
def get_all(db: Session):
    return db.query(Assignment).order_by(Assignment.created_at.desc()).all()


def get_by_id(db: Session, assignment_id: str):
    return db.query(Assignment).filter(Assignment.id == assignment_id).first()


# =====================================================
# 2) Tạo bài tập
# =====================================================
def create_assignment(
    db: Session,
    title: str,
    description: str | None,
    course_id: str,
    due_date: datetime | None = None,
    teacher_id: str | None = None,
    module_id: str | None = None,
):
    title, _course = _validate_assignment_payload(db, title, course_id, module_id, teacher_id)

    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title,
        description=(description or "").strip() or None,
        course_id=course_id,
        module_id=module_id or None,
        teacher_id=teacher_id or None,
        start_date=datetime.utcnow(),
        due_date=due_date,
        submission_type="individual",
        allowed_file_types="pdf,docx,zip",
        max_files=5,
        max_file_size_mb=50,
        total_points=10,
        allow_late_submission=0,
        late_penalty_percent=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        return new_assignment
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi khi tạo bài tập.")


# =====================================================
# 3) Cập nhật bài tập
# =====================================================
def update_assignment(
    db: Session,
    assignment_id: str,
    title: str,
    description: str | None,
    course_id: str,
    due_date: datetime | None = None,
    teacher_id: str | None = None,
    module_id: str | None = None,
):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại.")

    title, _course = _validate_assignment_payload(db, title, course_id, module_id, teacher_id)

    assignment.title = title
    assignment.description = (description or "").strip() or None
    assignment.course_id = course_id
    assignment.module_id = module_id or None
    assignment.teacher_id = teacher_id or None
    assignment.due_date = due_date
    assignment.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi khi cập nhật bài tập.")


# =====================================================
# 4) Xóa bài tập
# =====================================================
def delete_assignment(db: Session, assignment_id: str):
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return False

    try:
        db.delete(assignment)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi khi xóa bài tập.")


# =====================================================
# 5) Thống kê theo khóa học
# =====================================================
def get_assignment_analytics(db: Session, course_id: str):
    total_assignments = db.query(Assignment).filter(Assignment.course_id == course_id).count()

    total_submitted = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(Assignment.course_id == course_id)
        .count()
    )

    graded = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "graded",
        )
        .count()
    )

    late = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "late",
        )
        .count()
    )

    return {
        "total_assignments": total_assignments,
        "submitted": total_submitted,
        "graded": graded,
        "late": late,
    }


# =====================================================
# 6) Dashboard thống kê tổng hợp
# =====================================================
def get_global_assignment_report(db: Session):
    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(AssignmentSubmission).count()

    graded_submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.status == "graded")
        .count()
    )

    late_submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.status == "late")
        .count()
    )

    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(AssignmentSubmission.grade.isnot(None))
        .scalar()
    )

    return {
        "total_assignments": total_assignments,
        "total_submissions": total_submissions,
        "graded_submissions": graded_submissions,
        "late_submissions": late_submissions,
        "average_grade": round(avg_grade or 0, 2),
    }


# =====================================================
# 7) Thống kê theo giảng viên
# =====================================================
def get_teacher_assignment_stats(db: Session, teacher_id: str):
    results = (
        db.query(
            Course.course_name.label("course_name"),
            func.count(func.distinct(Assignment.id)).label("total_assignments"),
            func.count(func.distinct(AssignmentSubmission.id)).label("total_submissions"),
            func.avg(AssignmentSubmission.grade).label("average_grade"),
            func.sum(
                case((AssignmentSubmission.status == "late", 1), else_=0)
            ).label("late_submissions"),
        )
        .join(Assignment, Assignment.course_id == Course.id)
        .outerjoin(
            AssignmentSubmission,
            AssignmentSubmission.assignment_id == Assignment.id,
        )
        .filter(Assignment.teacher_id == teacher_id)
        .group_by(Course.id, Course.course_name)
        .all()
    )

    return [
        {
            "course_name": r.course_name,
            "total_assignments": r.total_assignments or 0,
            "total_submissions": r.total_submissions or 0,
            "late_submissions": r.late_submissions or 0,
            "average_grade": round(r.average_grade or 0, 2),
        }
        for r in results
    ]


# =====================================================
# 8) Thống kê cá nhân sinh viên
# =====================================================
def get_student_assignment_summary(db: Session, student_id: str):
    total_assigned = (
        db.query(func.count(func.distinct(AssignmentSubmission.assignment_id)))
        .filter(AssignmentSubmission.student_id == student_id)
        .scalar()
    )

    total_submitted = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.student_id == student_id)
        .count()
    )

    graded = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "graded",
        )
        .count()
    )

    late = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "late",
        )
        .count()
    )

    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.grade.isnot(None),
        )
        .scalar()
    )

    return {
        "total_assigned": total_assigned or 0,
        "total_submitted": total_submitted or 0,
        "graded": graded or 0,
        "late": late or 0,
        "avg_grade": round(avg_grade or 0, 2),
    }


# =====================================================
# 9) Xuất Excel
# =====================================================
def export_assignment_scores_to_excel(db: Session, assignment_id: str, file_path: str):
    results = (
        db.query(
            func.coalesce(UserProfile.full_name, User.username).label("Họ và tên"),
            AssignmentSubmission.status.label("Trạng thái"),
            AssignmentSubmission.grade.label("Điểm"),
            AssignmentSubmission.submission_time.label("Thời gian nộp"),
        )
        .select_from(AssignmentSubmission)
        .join(User, AssignmentSubmission.student_id == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.asc())
        .all()
    )

    df = pd.DataFrame(results) if results else pd.DataFrame(
        columns=["Họ và tên", "Trạng thái", "Điểm", "Thời gian nộp"]
    )

    df.to_excel(file_path, index=False, sheet_name="Assignment Scores")
    return file_path


# =====================================================
# 10) Chấm bài
# =====================================================
def grade_submission(
    db: Session,
    submission_id: str,
    grade: float,
    feedback: str,
    teacher_id: str | None = None,
):
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )

    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    if grade < 0:
        raise HTTPException(status_code=400, detail="Điểm không được âm.")

    submission.grade = grade
    submission.feedback = (feedback or "").strip() or None
    submission.status = "graded"
    submission.graded_at = datetime.utcnow()

    if teacher_id:
        teacher = db.query(User).filter(User.id == teacher_id).first()
        submission.graded_by = teacher.id if teacher else None
    else:
        submission.graded_by = None

    try:
        db.commit()
        db.refresh(submission)
        return submission
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Lỗi khi chấm bài.")