from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.classes import Class
from app.models.user import User
from app.models.quiz_attempt import QuizAttempt
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz import Quiz
from app.models.assignment import Assignment
from app.models.user_profile import UserProfile
from app.models.student_profile import StudentProfile

try:
    from app.models.class_enrollment import ClassEnrollment
except Exception:
    from app.models.enrollment import ClassEnrollment


ACTIVE_STATUSES = {"approved", "active", "completed"}


def get_teacher_classes(db: Session, teacher_id: str):
    return (
        db.query(Class)
        .filter(Class.homeroom_teacher_id == teacher_id)
        .order_by(Class.class_name.asc())
        .all()
    )


def get_teacher_class(db: Session, class_id: str, teacher_id: str):
    return (
        db.query(Class)
        .filter(
            Class.id == class_id,
            Class.homeroom_teacher_id == teacher_id,
        )
        .first()
    )


def get_class_info(db: Session, class_id: str):
    return db.query(Class).filter(Class.id == class_id).first()


def get_students_in_class(db: Session, class_id: str):
    role_col = getattr(ClassEnrollment, "role_in_class", None)

    query_entities = [
        User.id.label("user_id"),
        User.username.label("username"),
        User.email.label("email"),
        UserProfile.full_name.label("full_name"),
        StudentProfile.mssv.label("mssv"),
        ClassEnrollment.enrollment_status.label("enrollment_status"),
    ]

    if role_col is not None:
        query_entities.append(role_col.label("role_in_class"))

    rows = (
        db.query(*query_entities)
        .join(ClassEnrollment, ClassEnrollment.student_id == User.id)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.enrollment_status.in_(ACTIVE_STATUSES),
        )
        .order_by(UserProfile.full_name.asc(), User.username.asc())
        .all()
    )

    results = []
    for row in rows:
        results.append({
            "id": row.user_id,
            "full_name": row.full_name or row.username or "Không rõ",
            "email": row.email or "",
            "mssv": row.mssv or "-",
            "status": row.enrollment_status or "",
            "role_in_class": getattr(row, "role_in_class", None) or "Thành viên",
        })

    return results


def get_class_grade_statistics(db: Session, class_id: str):
    class_info = get_class_info(db, class_id)
    if not class_info:
        return []

    students = get_students_in_class(db, class_id)
    course_id = getattr(class_info, "course_id", None)

    results = []

    for student in students:
        quiz_query = db.query(func.avg(QuizAttempt.score)).filter(
            QuizAttempt.user_id == student["id"]
        )

        assignment_query = db.query(func.avg(AssignmentSubmission.grade)).filter(
            AssignmentSubmission.student_id == student["id"]
        )

        if course_id:
            quiz_query = (
                quiz_query.join(Quiz, Quiz.id == QuizAttempt.quiz_id)
                .filter(Quiz.course_id == course_id)
            )

            assignment_query = (
                assignment_query.join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
                .filter(Assignment.course_id == course_id)
            )

        quiz_avg = float(quiz_query.scalar() or 0)
        assign_avg = float(assignment_query.scalar() or 0)
        total_score = round((quiz_avg * 0.5 + assign_avg * 0.5), 2)

        results.append({
            "student_id": student["id"],
            "full_name": student["full_name"],
            "email": student["email"],
            "mssv": student["mssv"],
            "quiz_avg": round(quiz_avg, 2),
            "assignment_avg": round(assign_avg, 2),
            "total_score": total_score,
        })

    return results