from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.classes import Class
from app.models.enrollment import Enrollment
from app.models.user import User
from app.models.quiz_attempt import QuizAttempt
from app.models.assignment_submission import AssignmentSubmission

# =========================================================
# 📘 Danh sách lớp của giáo viên
# =========================================================
def get_teacher_classes(db: Session, teacher_id: str):
    """Lấy danh sách lớp do giáo viên phụ trách"""
    return db.query(Class).filter(Class.homeroom_teacher_id == teacher_id).all()

# =========================================================
# 📘 Thông tin lớp
# =========================================================
def get_class_info(db: Session, class_id: str):
    return db.query(Class).filter(Class.id == class_id).first()

# =========================================================
# 👨‍🎓 Danh sách học viên
# =========================================================
def get_students_in_class(db: Session, class_id: str):
    return (
        db.query(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.class_id == class_id, User.role == "student")
        .all()
    )

# =========================================================
# 📊 Thống kê điểm tổng hợp (Quiz + Assignment)
# =========================================================
def get_class_grade_statistics(db: Session, class_id: str):
    """
    Trả về danh sách thống kê điểm cho từng học viên trong lớp:
    - Quiz trung bình
    - Assignment trung bình
    - Điểm tổng hợp
    """
    # Lấy danh sách học viên trong lớp
    students = (
        db.query(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.class_id == class_id, User.role == "student")
        .all()
    )

    results = []
    for student in students:
        # --- Điểm quiz trung bình ---
        quiz_avg = (
            db.query(func.avg(QuizAttempt.score))
            .filter(QuizAttempt.user_id == student.id)
            .scalar()
        ) or 0

        # --- Điểm assignment trung bình ---
        assign_avg = (
            db.query(func.avg(AssignmentSubmission.grade))
            .filter(AssignmentSubmission.student_id == student.id)
            .scalar()
        ) or 0

        # --- Điểm tổng hợp (50/50) ---
        total_score = round((quiz_avg * 0.5 + assign_avg * 0.5), 2)

        results.append({
            "student": student,
            "quiz_avg": round(quiz_avg, 2),
            "assignment_avg": round(assign_avg, 2),
            "total_score": total_score
        })

    return results
