"""
📊 Assignment Analytics Service
Chức năng:
- Thống kê số lượng bài tập, bài đã nộp, chấm điểm, trễ hạn
- Xuất điểm bài tập ra file Excel (.xlsx)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User
from app.models.user_profile import UserProfile


# ======================================================
# 📈 1️⃣ Thống kê tổng quan bài tập theo khóa học
# ======================================================
def get_assignment_analytics(db: Session, course_id: str):
    """
    Trả về thống kê tổng quan bài tập của một khóa học:
    - Tổng số bài tập
    - Số bài đã nộp
    - Số bài đã chấm
    - Số bài trễ hạn
    """
    total_assignments = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.course_id == course_id)
        .scalar()
    )

    total_submitted = (
        db.query(func.count(AssignmentSubmission.id))
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .filter(Assignment.course_id == course_id)
        .scalar()
    )

    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "graded",
        )
        .scalar()
    )

    late = (
        db.query(func.count(AssignmentSubmission.id))
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "late",
        )
        .scalar()
    )

    return {
        "total_assignments": total_assignments or 0,
        "submitted": total_submitted or 0,
        "graded": graded or 0,
        "late": late or 0,
    }


# ======================================================
# 📤 2️⃣ Xuất điểm bài tập ra Excel
# ======================================================
def export_assignment_scores_to_excel(db: Session, assignment_id: str, file_path: str):
    """
    Xuất danh sách điểm của một bài tập ra file Excel (.xlsx)
    Gồm: Họ tên, Trạng thái, Điểm, Thời gian nộp
    """
    results = (
        db.query(
            UserProfile.full_name.label("Họ và tên"),
            AssignmentSubmission.status.label("Trạng thái"),
            AssignmentSubmission.grade.label("Điểm"),
            AssignmentSubmission.submission_time.label("Thời gian nộp"),
        )
        .join(AssignmentSubmission, AssignmentSubmission.student_id == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .all()
    )

    if not results:
        df = pd.DataFrame(columns=["Họ và tên", "Trạng thái", "Điểm", "Thời gian nộp"])
    else:
        rows = [
            {
                "Họ và tên": row[0],
                "Trạng thái": row[1],
                "Điểm": row[2],
                "Thời gian nộp": row[3],
            }
            for row in results
        ]
        df = pd.DataFrame(rows)

    df.to_excel(file_path, index=False, sheet_name="Assignment Scores")
    return file_path


# ======================================================
# 🧮 3️⃣ (Tùy chọn) Thống kê chi tiết từng bài tập
# ======================================================
def get_detailed_analytics(db: Session, assignment_id: str):
    """
    Lấy chi tiết thống kê 1 bài tập:
    - Tổng lượt nộp
    - Số bài đã chấm
    - Trung bình điểm
    - Số bài trễ
    """
    total_submissions = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .scalar()
    )

    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.status == "graded",
        )
        .scalar()
    )

    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.grade.isnot(None),
        )
        .scalar()
    )

    late = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.status == "late",
        )
        .scalar()
    )

    return {
        "total_submissions": total_submissions or 0,
        "graded": graded or 0,
        "avg_grade": round(avg_grade or 0, 2),
        "late": late or 0,
    }