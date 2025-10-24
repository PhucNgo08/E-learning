"""
📘 Assignment Service (Admin)
CRUD + Thống kê + Xuất Excel cho bài tập.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User
from datetime import datetime
import pandas as pd
import uuid


# =====================================================
# 🧩 1️⃣ Lấy danh sách & chi tiết
# =====================================================
def get_all(db: Session):
    """Admin xem toàn bộ bài tập"""
    return db.query(Assignment).order_by(Assignment.created_at.desc()).all()


def get_by_id(db: Session, assignment_id: str):
    """Lấy thông tin chi tiết 1 bài tập"""
    return db.query(Assignment).filter(Assignment.id == assignment_id).first()


# =====================================================
# ➕ 2️⃣ Tạo bài tập mới
# =====================================================
def create_assignment(
    db: Session,
    title: str,
    description: str,
    course_id: str,
    due_date: datetime = None,
    teacher_id: str = None,
    module_id: str = None
):
    """
    Admin tạo bài tập mới (có thể gán teacher_id hoặc để None).
    """
    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title.strip(),
        description=description.strip() if description else None,
        course_id=course_id,
        module_id=module_id,
        teacher_id=teacher_id if teacher_id else None,
        start_date=datetime.utcnow(),
        due_date=due_date,
        submission_type="individual",
        total_points=10,
        allow_late_submission=False,
        late_penalty_percent=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        print(f"✅ [Admin] Đã tạo bài tập: {title}")
        return new_assignment
    except Exception as e:
        db.rollback()
        print(f"❌ [Admin] Lỗi khi tạo bài tập: {e}")
        raise


# =====================================================
# ✏️ 3️⃣ Cập nhật bài tập
# =====================================================
def update_assignment(db: Session, assignment_id: str, title: str, description: str):
    """Cập nhật thông tin bài tập"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return None

    assignment.title = title.strip()
    assignment.description = description.strip() if description else None
    assignment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(assignment)
    print(f"✏️ [Admin] Đã cập nhật bài tập: {title}")
    return assignment


# =====================================================
# 🗑️ 4️⃣ Xóa bài tập
# =====================================================
def delete_assignment(db: Session, assignment_id: str):
    """Admin xóa bài tập bất kỳ"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if assignment:
        db.delete(assignment)
        db.commit()
        print(f"🗑️ [Admin] Đã xóa bài tập: {assignment.title}")
        return True
    return False


# =====================================================
# 📊 5️⃣ Thống kê tổng quan
# =====================================================
def get_statistics(db: Session):
    """Thống kê tổng quan bài tập"""
    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(AssignmentSubmission).count()
    graded = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.status == "graded"
    ).count()

    return {
        "total_assignments": total_assignments,
        "total_submissions": total_submissions,
        "graded": graded
    }


# =====================================================
# 📈 6️⃣ Thống kê theo khóa học
# =====================================================
def get_assignment_analytics(db: Session, course_id: str):
    """Thống kê bài tập theo khóa học"""
    total_assignments = (
        db.query(func.count(Assignment.id))
        .filter(Assignment.course_id == course_id)
        .scalar()
    )
    total_submitted = (
        db.query(func.count(AssignmentSubmission.id))
        .join(Assignment)
        .filter(Assignment.course_id == course_id)
        .scalar()
    )
    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.status == "graded")
        .scalar()
    )
    late = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.status == "late")
        .scalar()
    )

    return {
        "total_assignments": total_assignments or 0,
        "submitted": total_submitted or 0,
        "graded": graded or 0,
        "late": late or 0,
    }


# =====================================================
# 📤 7️⃣ Xuất điểm ra Excel
# =====================================================
def export_assignment_scores_to_excel(db: Session, assignment_id: str, file_path: str):
    """
    Xuất danh sách điểm bài tập ra Excel (.xlsx)
    """
    results = (
        db.query(
            User.full_name.label("Họ và tên"),
            AssignmentSubmission.status.label("Trạng thái"),
            AssignmentSubmission.grade.label("Điểm"),
            AssignmentSubmission.submission_time.label("Thời gian nộp")
        )
        .join(AssignmentSubmission, AssignmentSubmission.student_id == User.id)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .all()
    )

    if not results:
        df = pd.DataFrame(columns=["Họ và tên", "Trạng thái", "Điểm", "Thời gian nộp"])
    else:
        df = pd.DataFrame(results)

    df.to_excel(file_path, index=False, sheet_name="Assignment Scores")
    print(f"📤 [Admin] Xuất Excel: {file_path}")
    return file_path


# =====================================================
# 🧮 8️⃣ Thống kê chi tiết từng bài tập
# =====================================================
def get_detailed_analytics(db: Session, assignment_id: str):
    """Lấy chi tiết thống kê từng bài tập"""
    total_submissions = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .scalar()
    )
    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.status == "graded"
        )
        .scalar()
    )
    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.grade.isnot(None)
        )
        .scalar()
    )
    late = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.status == "late"
        )
        .scalar()
    )

    return {
        "total_submissions": total_submissions or 0,
        "graded": graded or 0,
        "avg_grade": round(avg_grade or 0, 2),
        "late": late or 0,
    }


# =====================================================
# 📊 9️⃣ Thống kê tổng hợp toàn hệ thống
# =====================================================
def get_global_assignment_report(db: Session):
    """
    Thống kê toàn bộ bài tập trong hệ thống:
    - Tổng số bài tập
    - Tổng số lượt nộp
    - Tổng bài đã chấm
    - Bài nộp trễ
    - Điểm trung bình chung
    """
    total_assignments = db.query(func.count(Assignment.id)).scalar()
    total_submissions = db.query(func.count(AssignmentSubmission.id)).scalar()
    graded_submissions = db.query(func.count(AssignmentSubmission.id)).filter(
        AssignmentSubmission.status == "graded"
    ).scalar()
    late_submissions = db.query(func.count(AssignmentSubmission.id)).filter(
        AssignmentSubmission.status == "late"
    ).scalar()
    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(AssignmentSubmission.grade.isnot(None))
        .scalar()
    )

    return {
        "total_assignments": total_assignments or 0,
        "total_submissions": total_submissions or 0,
        "graded_submissions": graded_submissions or 0,
        "late_submissions": late_submissions or 0,
        "average_grade": round(avg_grade or 0, 2),
    }


# =====================================================
# 🧑‍🏫 🔟 Thống kê theo giảng viên & khóa học
# =====================================================
def get_teacher_assignment_stats(db: Session, teacher_id: str):
    """
    Thống kê bài tập theo từng khóa học mà giảng viên phụ trách.
    Gồm: tổng bài tập, tổng lượt nộp, bài trễ, điểm trung bình.
    """
    from app.models.course import Course  # tránh circular import

    results = (
        db.query(
            Course.course_name.label("course_name"),
            func.count(Assignment.id).label("total_assignments"),
            func.count(AssignmentSubmission.id).label("total_submissions"),
            func.avg(AssignmentSubmission.grade).label("average_grade"),
            func.count(
                func.nullif(AssignmentSubmission.status != "late", True)
            ).label("late_submissions"),
        )
        .join(Assignment, Assignment.course_id == Course.id)
        .outerjoin(
            AssignmentSubmission, AssignmentSubmission.assignment_id == Assignment.id
        )
        .filter(Assignment.teacher_id == teacher_id)
        .group_by(Course.id)
        .all()
    )

    stats = []
    for r in results:
        stats.append({
            "course_name": r.course_name,
            "total_assignments": r.total_assignments or 0,
            "total_submissions": r.total_submissions or 0,
            "late_submissions": r.late_submissions or 0,
            "average_grade": round(r.average_grade or 0, 2),
        })

    return stats


# =====================================================
# 🎓 1️⃣1️⃣ Thống kê cá nhân sinh viên
# =====================================================
def get_student_assignment_summary(db: Session, student_id: str):
    """
    Lấy thống kê bài tập cá nhân cho sinh viên.
    Gồm: số bài đã giao, đã nộp, đã chấm, nộp trễ, điểm trung bình.
    """
    total_assigned = db.query(func.count(Assignment.id)).scalar()
    total_submitted = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.student_id == student_id)
        .scalar()
    )
    graded = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "graded",
        )
        .scalar()
    )
    late = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "late",
        )
        .scalar()
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
