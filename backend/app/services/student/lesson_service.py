"""
==========================================================
📗 Service: Lesson (Bài học)
Xử lý module, bài học, tiến độ và ghi chú học viên
==========================================================
"""

from sqlalchemy.orm import Session
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.lesson_progress import LessonProgress
from app.models.lesson_note import LessonNote
from datetime import datetime
import uuid
import traceback


# =====================================================
# 📚 Lấy danh sách bài học theo khóa học
# =====================================================
def get_modules_by_course(db: Session, course_id: str):
    """Lấy danh sách tất cả bài học thuộc khóa học (join qua bảng Module)."""
    try:
        lessons = (
            db.query(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .filter(Module.course_id == course_id)
            .order_by(Lesson.lesson_number.asc())
            .all()
        )
        return lessons
    except Exception as e:
        print("❌ [get_modules_by_course] Lỗi:", e)
        traceback.print_exc()
        return []


# =====================================================
# 📘 Lấy chi tiết một bài học
# =====================================================
def get_lesson_detail(db: Session, lesson_id: str):
    """Lấy thông tin chi tiết một bài học."""
    try:
        return db.query(Lesson).filter(Lesson.id == lesson_id).first()
    except Exception as e:
        print("❌ [get_lesson_detail] Lỗi:", e)
        traceback.print_exc()
        return None


# =====================================================
# ✅ Đánh dấu bài học hoàn thành
# =====================================================
def mark_lesson_completed(db: Session, user_id: str, lesson_id: str):
    """Đánh dấu bài học hoàn thành."""
    try:
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
        db.refresh(progress)
        print(f"✅ [mark_lesson_completed] user={user_id}, lesson={lesson_id}")
        return progress
    except Exception as e:
        db.rollback()
        print("❌ [mark_lesson_completed] Lỗi:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📗 Lấy danh sách bài học theo module
# =====================================================
def get_lessons_by_module(db: Session, module_id: str):
    """Lấy danh sách bài học theo module (dành cho học viên)."""
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
        print("❌ [get_lessons_by_module] Lỗi:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📊 Lấy tiến độ bài học của học viên
# =====================================================
def get_lesson_progress(db: Session, user_id: str, lesson_id: str):
    """Truy xuất tiến độ của học viên cho một bài học."""
    try:
        return (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
            .first()
        )
    except Exception as e:
        print("❌ [get_lesson_progress] Lỗi:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📝 Ghi chú bài học (lấy + lưu)
# =====================================================
def get_notes_by_lesson(db: Session, user_id: str, lesson_id: str):
    """Lấy danh sách ghi chú của học viên cho một bài học."""
    try:
        return (
            db.query(LessonNote)
            .filter(
                LessonNote.user_id == user_id,
                LessonNote.lesson_id == lesson_id,
            )
            .order_by(LessonNote.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_notes_by_lesson] Lỗi:", e)
        traceback.print_exc()
        return []


def add_note_to_lesson(db: Session, user_id: str, lesson_id: str, content: str):
    """Thêm ghi chú mới cho bài học."""
    try:
        note = LessonNote(
            id=str(uuid.uuid4()),
            user_id=user_id,
            lesson_id=lesson_id,
            content=content.strip(),
            created_at=datetime.utcnow(),
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note
    except Exception as e:
        db.rollback()
        print("❌ [add_note_to_lesson] Lỗi:", e)
        traceback.print_exc()
        return None


# =====================================================
# 🎓 Lấy danh sách module mà sinh viên đã ghi danh
# =====================================================
def get_modules_for_student(db: Session, user_id: str):
    """Lấy tất cả module mà sinh viên đã ghi danh."""
    try:
        from app.models.enrollment import Enrollment
        from app.models.course import Course

        return (
            db.query(Module)
            .join(Course, Module.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == user_id)
            .order_by(Module.created_at.desc())
            .all()
        )
    except Exception as e:
        print("❌ [get_modules_for_student] Lỗi:", e)
        traceback.print_exc()
        return []
# =====================================================
# 📊 Tiến độ học tập tổng thể của học viên
# =====================================================
def get_learning_progress(db: Session, user_id: str):
    """
    Lấy tiến độ học tập của học viên trong tất cả khóa học.
    Trả về danh sách {course, total_lessons, completed_lessons, completion_rate}.
    """
    try:
        from app.models.course import Course
        from app.models.lesson import Lesson
        from app.models.lesson_progress import LessonProgress

        # Lấy tất cả khóa học mà học viên có bài học đã học
        courses = (
            db.query(Course)
            .join(Lesson, Lesson.course_id == Course.id)
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .filter(LessonProgress.user_id == user_id)
            .distinct()
            .all()
        )

        progress_list = []
        for course in courses:
            total_lessons = db.query(Lesson).filter(Lesson.course_id == course.id).count()

            completed_lessons = (
                db.query(LessonProgress)
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .filter(
                    Lesson.course_id == course.id,
                    LessonProgress.user_id == user_id,
                    LessonProgress.progress_status == "completed"
                )
                .count()
            )

            completion_rate = 0
            if total_lessons > 0:
                completion_rate = round((completed_lessons / total_lessons) * 100, 2)

            progress_list.append({
                "course": course,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "completion_rate": completion_rate
            })

        print(f"📊 [get_learning_progress] user={user_id}, courses={len(progress_list)}")
        return progress_list

    except Exception as e:
        print("❌ [get_learning_progress] Lỗi:", e)
        traceback.print_exc()
        return []
