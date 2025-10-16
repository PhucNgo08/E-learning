from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz_attempt import QuizAttempt
from app.models.lesson_progress import LessonProgress
from app.models.course_review import CourseReview

# 📊 Tổng hợp thống kê nhanh
def get_dashboard_stats(db: Session):
    try:
        total_students = db.query(Enrollment).count()
        total_courses = db.query(Course).count()
        total_quizzes = db.query(QuizAttempt).count()
        total_reviews = db.query(CourseReview).count()
        avg_progress = db.query(LessonProgress).count()  # có thể thay bằng % TB sau

        return {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_quizzes": total_quizzes,
            "total_reviews": total_reviews,
            "avg_progress": avg_progress,
        }
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi lấy thống kê: {str(e)}")


# 📈 Sinh báo cáo theo loại
def generate_report(report_type: str, db: Session):
    try:
        if report_type == "course":
            data = db.query(Course).all()
        elif report_type == "enrollment":
            data = db.query(Enrollment).all()
        elif report_type == "quiz":
            data = db.query(QuizAttempt).all()
        else:
            data = []
        return data
    except SQLAlchemyError as e:
        raise RuntimeError(f"Lỗi khi tạo báo cáo: {str(e)}")
# ❌ Xóa báo cáo (giả lập, nếu có bảng report_logs thì thao tác tại đây)
def delete_report(report_id: str):
    # Giả lập xóa report (nếu có bảng report_logs thì thao tác tại đây)
    return True