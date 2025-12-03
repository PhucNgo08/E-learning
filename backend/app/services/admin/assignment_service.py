"""
📘 Assignment Service (Admin)
CRUD + Thống kê + Xuất Excel cho bài tập.
✓ Hỗ trợ validate course_id, module_id, teacher_id
✓ Không còn lỗi MySQL FOREIGN KEY (1452)
✓ Tối ưu truy vấn và logic đúng chuẩn database mới
"""

from sqlalchemy import case
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime
import pandas as pd
import uuid

# Models
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.user import User
from app.models.course import Course
from app.models.module import Module


# =====================================================
# 🧩 1️⃣ Lấy danh sách & chi tiết
# =====================================================
def get_all(db: Session):
    """Admin xem toàn bộ bài tập"""
    return (
        db.query(Assignment)
        .order_by(Assignment.created_at.desc())
        .all()
    )


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
    Admin tạo bài tập mới.
    Validate đầy đủ:
      - course_id phải tồn tại
      - module_id phải thuộc đúng course_id (nếu có)
      - teacher_id phải tồn tại (nếu có)
    """

    # -------------------------------
    # 1️⃣ Validate course_id
    # -------------------------------
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=400, detail="❌ Course ID không tồn tại!")

    # -------------------------------
    # 2️⃣ Validate module_id (optional)
    # -------------------------------
    if module_id:
        module = db.query(Module).filter(Module.id == module_id).first()
        if not module:
            raise HTTPException(status_code=400, detail="❌ Module ID không tồn tại!")
        if module.course_id != course_id:
            raise HTTPException(
                status_code=400,
                detail="❌ Module không thuộc khóa học bạn đã chọn!"
            )

    # -------------------------------
    # 3️⃣ Validate teacher_id (optional)
    # -------------------------------
    if teacher_id:
        teacher = db.query(User).filter(
            User.id == teacher_id,
            User.role.in_(["teacher", "admin"])
        ).first()

        if not teacher:
            raise HTTPException(status_code=400, detail="❌ Teacher ID không hợp lệ!")

    # -------------------------------
    # 4️⃣ Tạo Assignment
    # -------------------------------
    new_assignment = Assignment(
        id=str(uuid.uuid4()),
        title=title.strip(),
        description=description.strip() if description else None,
        course_id=course_id,
        module_id=module_id,
        teacher_id=teacher_id,
        start_date=datetime.utcnow(),
        due_date=due_date,

        # DB defaults
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
        print(f"✅ [Admin] Đã tạo bài tập: {title}")
        return new_assignment

    except Exception as e:
        db.rollback()
        print(f"❌ [Admin] Lỗi khi tạo bài tập: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi tạo bài tập!")


# =====================================================
# ✏️ 3️⃣ Cập nhật bài tập
# =====================================================
def update_assignment(db: Session, assignment_id: str, title: str, description: str):
    """Cập nhật thông tin bài tập"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Bài tập không tồn tại!")

    assignment.title = title.strip()
    assignment.description = description.strip() if description else None
    assignment.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(assignment)
    print(f"✏️ [Admin] Đã cập nhật bài tập: {assignment.title}")
    return assignment


# =====================================================
# 🗑️ 4️⃣ Xóa bài tập
# =====================================================
def delete_assignment(db: Session, assignment_id: str):
    """Admin xóa bài tập bất kỳ"""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        return False

    db.delete(assignment)
    db.commit()

    print(f"🗑️ [Admin] Đã xóa bài tập: {assignment.title}")
    return True


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

    total_assignments = db.query(Assignment).filter(
        Assignment.course_id == course_id
    ).count()

    total_submitted = (
        db.query(AssignmentSubmission)
        .join(Assignment)
        .filter(Assignment.course_id == course_id)
        .count()
    )

    graded = (
        db.query(AssignmentSubmission)
        .join(Assignment)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "graded"
        )
        .count()
    )

    late = (
        db.query(AssignmentSubmission)
        .join(Assignment)
        .filter(
            Assignment.course_id == course_id,
            AssignmentSubmission.status == "late"
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
# 📤 7️⃣ Xuất điểm ra Excel
# =====================================================
def export_assignment_scores_to_excel(db: Session, assignment_id: str, file_path: str):
    """Xuất danh sách điểm bài tập ra Excel (.xlsx)"""

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

    df = pd.DataFrame(results) if results else pd.DataFrame(
        columns=["Họ và tên", "Trạng thái", "Điểm", "Thời gian nộp"]
    )

    df.to_excel(file_path, index=False, sheet_name="Assignment Scores")
    print(f"📤 Excel exported: {file_path}")
    return file_path


# =====================================================
# 🧮 8️⃣ Thống kê chi tiết từng bài tập
# =====================================================
def get_detailed_analytics(db: Session, assignment_id: str):
    """Thống kê chi tiết bài tập"""

    total_submissions = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id
    ).count()

    graded = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.status == "graded"
    ).count()

    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.grade.isnot(None)
        )
        .scalar()
    )

    late = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.status == "late"
    ).count()

    return {
        "total_submissions": total_submissions,
        "graded": graded,
        "avg_grade": round(avg_grade or 0, 2),
        "late": late
    }


# =====================================================
# 📊 9️⃣ Thống kê tổng hợp toàn hệ thống
# =====================================================
def get_global_assignment_report(db: Session):
    """Thống kê toàn hệ thống"""

    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(AssignmentSubmission).count()

    graded_submissions = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.status == "graded"
    ).count()

    late_submissions = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.status == "late"
    ).count()

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
        "average_grade": round(avg_grade or 0, 2)
    }


# =====================================================
# 🧑‍🏫 🔟 Thống kê theo giảng viên
# =====================================================
def get_teacher_assignment_stats(db: Session, teacher_id: str):
    """Thống kê bài tập theo từng khóa học mà giảng viên phụ trách."""

    results = (
        db.query(
            Course.course_name.label("course_name"),
            func.count(Assignment.id).label("total_assignments"),
            func.count(AssignmentSubmission.id).label("total_submissions"),
            func.avg(AssignmentSubmission.grade).label("average_grade"),
            func.sum(
                case(
                    (AssignmentSubmission.status == "late", 1),
                    else_=0
                )
            ).label("late_submissions"),
        )
        .join(Assignment, Assignment.course_id == Course.id)
        .outerjoin(
            AssignmentSubmission,
            AssignmentSubmission.assignment_id == Assignment.id
        )
        .filter(Assignment.teacher_id == teacher_id)
        .group_by(Course.id)
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
# 🎓 1️⃣1️⃣ Thống kê cá nhân sinh viên
# =====================================================
def get_student_assignment_summary(db: Session, student_id: str):
    """Thống kê bài tập cá nhân cho sinh viên."""

    total_assigned = (
        db.query(Assignment)
        .join(AssignmentSubmission, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(AssignmentSubmission.student_id == student_id)
        .count()
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
            AssignmentSubmission.status == "graded"
        )
        .count()
    )

    late = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "late"
        )
        .count()
    )

    avg_grade = (
        db.query(func.avg(AssignmentSubmission.grade))
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.grade.isnot(None)
        )
        .scalar()
    )

    return {
        "total_assigned": total_assigned or 0,
        "total_submitted": total_submitted or 0,
        "graded": graded or 0,
        "late": late or 0,
        "avg_grade": round(avg_grade or 0, 2)
    }
# =====================================================
# 📝 1️⃣2️⃣ Chấm bài (Grade Submission)
# =====================================================
def grade_submission(
    db: Session,
    submission_id: str,
    grade: float,
    feedback: str,
    teacher_id: str
):
    """Giảng viên/Admin chấm điểm bài nộp"""

    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission không tồn tại!")

    # Cập nhật thông tin chấm điểm
    submission.grade = grade
    submission.feedback = feedback
    submission.status = "graded"
    submission.graded_by = teacher_id
    submission.graded_at = datetime.utcnow()

    # Cập nhật thống kê cho giáo viên
    teacher = db.query(User).filter(User.id == teacher_id).first()
    if teacher:
        teacher.total_assignments_graded += 1

    db.commit()
    db.refresh(submission)

    print(f"✔️ [GRADE] Teacher {teacher_id} graded submission {submission_id}")

    return submission
