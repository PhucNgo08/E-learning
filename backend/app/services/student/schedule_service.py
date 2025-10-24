"""
📒 Service: Schedule (Lịch học & tiến độ học tập)
"""

from sqlalchemy.orm import Session
from app.models.class_schedule import ClassSchedule
from app.models.lesson_progress import LessonProgress

def get_student_schedule(db: Session, user_id: str):
    """Lấy lịch học của học viên"""
    return db.query(ClassSchedule).all()

def get_learning_progress(db: Session, user_id: str):
    """Tính tiến độ học viên"""
    lessons_done = db.query(LessonProgress).filter(LessonProgress.user_id == user_id, LessonProgress.progress_status == "completed").count()
    total_lessons = db.query(LessonProgress).filter(LessonProgress.user_id == user_id).count()
    percent = (lessons_done / total_lessons * 100) if total_lessons > 0 else 0
    return {"user_id": user_id, "progress_percent": percent}
