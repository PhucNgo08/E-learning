from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.quiz_attempt import QuizAttempt
from app.models.lesson_progress import LessonProgress

def get_teacher_statistics(db: Session):
    """📊 Thống kê tổng quan cho dashboard giáo viên"""
    try:
        total_assignments = db.query(func.count(Assignment.id)).scalar()
        total_submissions = db.query(func.count(AssignmentSubmission.id)).scalar()
        avg_quiz_score = db.query(func.avg(QuizAttempt.score)).scalar()
        completed_lessons = (
            db.query(func.count(LessonProgress.id))
            .filter(LessonProgress.progress_status == "completed")
            .scalar()
        )

        return {
            "total_assignments": total_assignments or 0,
            "total_submissions": total_submissions or 0,
            "avg_quiz_score": round(avg_quiz_score or 0, 2),
            "completed_lessons": completed_lessons or 0,
        }

    except Exception as e:
        print(f"[❌ ERROR] get_teacher_statistics: {e}")
        return {
            "total_assignments": 0,
            "total_submissions": 0,
            "avg_quiz_score": 0,
            "completed_lessons": 0,
        }
