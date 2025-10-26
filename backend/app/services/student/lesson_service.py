"""
📗 Service: Lesson (Bài học)
Xử lý module, bài học, tiến độ và ghi chú học viên
"""

from sqlalchemy.orm import Session
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.lesson_progress import LessonProgress
from app.models.lesson_note import LessonNote   # ✅ nếu bạn có model ghi chú
from datetime import datetime
import uuid


# =====================================================
# 📚 Lấy danh sách bài học theo khóa học
# =====================================================
def get_modules_by_course(db: Session, course_id: str):
    """Lấy danh sách bài học thuộc khóa học"""
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == course_id)
        .order_by(Lesson.lesson_number)
        .all()
    )


# =====================================================
# 📘 Lấy chi tiết một bài học
# =====================================================
def get_lesson_detail(db: Session, lesson_id: str):
    """Lấy thông tin chi tiết một bài học"""
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()


# =====================================================
# ✅ Đánh dấu bài học hoàn thành
# =====================================================
def mark_lesson_completed(db: Session, user_id: str, lesson_id: str):
    """Đánh dấu bài học hoàn thành"""
    progress = (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )

    if not progress:
        progress = LessonProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            lesson_id=lesson_id,
            progress_status="completed",
            completion_percentage=100,
            completed_at=datetime.utcnow(),
        )
        db.add(progress)
    else:
        progress.progress_status = "completed"
        progress.completion_percentage = 100
        progress.completed_at = datetime.utcnow()

    db.commit()
    return progress


# =====================================================
# 📗 Lấy danh sách bài học theo module
# =====================================================
def get_lessons_by_module(db: Session, module_id: str):
    """Lấy danh sách bài học theo module (dành cho học viên)"""
    try:
        module = db.query(Module).filter(Module.id == module_id).first()
        if not module:
            return None

        lessons = (
            db.query(Lesson)
            .filter(Lesson.module_id == module_id)
            .order_by(Lesson.lesson_number.asc())
            .all()
        )
        return {"module": module, "lessons": lessons}
    except Exception as e:
        print("❌ [get_lessons_by_module] Error:", e)
        return None


# =====================================================
# 📊 Lấy tiến độ bài học của học viên
# =====================================================
def get_lesson_progress(db: Session, user_id: str, lesson_id: str):
    """Truy xuất tiến độ của học viên cho một bài học"""
    return (
        db.query(LessonProgress)
        .filter(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
        .first()
    )


# =====================================================
# 📝 Ghi chú bài học (lấy + lưu)
# =====================================================
def get_notes_by_lesson(db: Session, user_id: str, lesson_id: str):
    """Lấy danh sách ghi chú của học viên cho một bài học"""
    return (
        db.query(LessonNote)
        .filter(
            LessonNote.user_id == user_id,
            LessonNote.lesson_id == lesson_id,
        )
        .order_by(LessonNote.created_at.desc())
        .all()
    )


def add_note_to_lesson(db: Session, user_id: str, lesson_id: str, content: str):
    """Thêm ghi chú mới cho bài học"""
    note = LessonNote(
        id=str(uuid.uuid4()),
        user_id=user_id,
        lesson_id=lesson_id,
        content=content,
        created_at=datetime.utcnow(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

def get_modules_for_student(db: Session, user_id: str):
    """
    Lấy tất cả module mà sinh viên đã ghi danh
    """
    from app.models.enrollment import Enrollment
    from app.models.course import Course
    from app.models.module import Module

    return (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == user_id)
        .order_by(Module.created_at.desc())
        .all()
    )
