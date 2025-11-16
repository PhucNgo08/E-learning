# app/services/report_service.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz_attempt import QuizAttempt
from app.models.lesson_progress import LessonProgress
from app.models.course_review import CourseReview


# ============================================================
# 📊 Dashboard Stats
# ============================================================
def get_dashboard_stats(db: Session):
    try:
        total_students = db.query(Enrollment).count()
        total_courses = db.query(Course).count()
        total_quizzes = db.query(QuizAttempt).count()
        total_reviews = db.query(CourseReview).count()

        # Tính tỷ lệ hoàn thành bài học trung bình
        progress_items = db.query(LessonProgress).all()
        if progress_items:
            avg_progress = sum([item.completion_percentage for item in progress_items]) / len(progress_items)
        else:
            avg_progress = 0

        return {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_quizzes": total_quizzes,
            "total_reviews": total_reviews,
            "avg_progress": round(avg_progress, 2),
        }

    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy thống kê: {str(e)}")


# ============================================================
# 📈 Generate Report
# ============================================================
def generate_report(report_type: str, db: Session):
    try:
        if report_type == "course":
            return db.query(Course).all()
        elif report_type == "enrollment":
            return db.query(Enrollment).all()
        elif report_type == "quiz":
            return db.query(QuizAttempt).all()
        else:
            return []

    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi tạo báo cáo: {str(e)}")


# ============================================================
# ❌ Delete Report — mô phỏng
# ============================================================
def delete_report(report_id: str):
    return True  # backend chưa có bảng report_logs
