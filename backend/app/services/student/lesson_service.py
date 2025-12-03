"""
==========================================================
📗 SERVICE: LESSON (FINAL 2025)
Xử lý module, bài học, tiến độ và ghi chú học viên
==========================================================
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import traceback

from app.models.lesson import Lesson
from app.models.module import Module
from app.models.lesson_progress import LessonProgress
from app.models.lesson_note import LessonNote


# =====================================================
# 📕 1) Lấy chi tiết bài học
# =====================================================
def get_lesson_detail(db: Session, lesson_id: str):
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        return lesson
    except Exception as e:
        print("❌ [get_lesson_detail] Error:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📘 2) Lấy danh sách bài học theo module
# =====================================================
def get_lessons_by_module(db: Session, module_id: str):
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
        traceback.print_exc()
        return None


# =====================================================
# 📗 3) Lấy danh sách bài học theo course
# =====================================================
def get_modules_by_course(db: Session, course_id: str):
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
        print("❌ [get_modules_by_course] Error:", e)
        traceback.print_exc()
        return []


# =====================================================
# 🧩 4) Lấy tiến độ bài học
# =====================================================
def get_lesson_progress(db: Session, user_id: str, lesson_id: str):
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
        print("❌ [get_lesson_progress] Error:", e)
        traceback.print_exc()
        return None


# =====================================================
# 🎯 5) Đánh dấu bài học hoàn thành
# =====================================================
def mark_lesson_completed(db: Session, user_id: str, lesson_id: str):
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
        return progress

    except Exception as e:
        db.rollback()
        print("❌ [mark_lesson_completed] Error:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📝 6) Lấy ghi chú bài học
# =====================================================
def get_notes_by_lesson(db: Session, user_id: str, lesson_id: str):
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
        print("❌ [get_notes_by_lesson] Error:", e)
        traceback.print_exc()
        return []


# =====================================================
# 📝 7) Thêm ghi chú
# =====================================================
def add_note_to_lesson(db: Session, user_id: str, lesson_id: str, content: str):
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
        print("❌ [add_note_to_lesson] Error:", e)
        traceback.print_exc()
        return None


# =====================================================
# 📚 8) Module của học viên (course đã ghi danh)
# =====================================================
def get_modules_for_student(db: Session, user_id: str):
    try:
        from app.models.enrollment import Enrollment
        from app.models.course import Course

        modules = (
            db.query(Module)
            .join(Course, Module.course_id == Course.id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .filter(Enrollment.user_id == user_id)
            .order_by(Module.created_at.desc())
            .all()
        )

        return modules

    except Exception as e:
        print("❌ [get_modules_for_student] Error:", e)
        traceback.print_exc()
        return []


# =====================================================
# 📊 9) Tiến độ học tập tổng thể
# =====================================================
def get_learning_progress(db: Session, user_id: str):
    try:
        from app.models.course import Course

        # Lấy tất cả course có bài học của user
        courses = (
            db.query(Course)
            .join(Module, Module.course_id == Course.id)
            .join(Lesson, Lesson.module_id == Module.id)
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .filter(LessonProgress.user_id == user_id)
            .distinct()
            .all()
        )

        progress_list = []

        for course in courses:
            # Tổng bài học của course
            total_lessons = (
                db.query(Lesson)
                .join(Module, Lesson.module_id == Module.id)
                .filter(Module.course_id == course.id)
                .count()
            )

            # Bài học đã completed
            completed_lessons = (
                db.query(LessonProgress)
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    Module.course_id == course.id,
                    LessonProgress.user_id == user_id,
                    LessonProgress.progress_status == "completed",
                )
                .count()
            )

            completion_rate = (
                round((completed_lessons / total_lessons) * 100, 2)
                if total_lessons > 0 else 0
            )

            progress_list.append({
                "course": course,
                "total_lessons": total_lessons,
                "completed_lessons": completed_lessons,
                "completion_rate": completion_rate,
            })

        return progress_list

    except Exception as e:
        print("❌ [get_learning_progress] Error:", e)
        traceback.print_exc()
        return []


# =====================================================
# 🔍 10) Lấy đầy đủ cấu trúc (lesson → module → course)
# =====================================================
def get_lesson_full_structure(db: Session, lesson_id: str):
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return None

        module = db.query(Module).filter(Module.id == lesson.module_id).first()
        if not module:
            return None

        from app.models.course import Course
        course = db.query(Course).filter(Course.id == module.course_id).first()

        return {
            "lesson": lesson,
            "module": module,
            "course": course,
        }

    except Exception as e:
        print("❌ [get_lesson_full_structure] Error:", e)
        traceback.print_exc()
        return None
# =====================================================
# 🧩 11) Lấy quiz theo bài học (FIX QUAN TRỌNG)
# =====================================================
def get_quiz_by_lesson(db: Session, lesson_id: str):
    try:
        from app.models.quiz import Quiz
        from app.models.question import Question
        from app.models.question_option import QuestionOption
        from sqlalchemy.orm import joinedload

        quiz = (
            db.query(Quiz)
            .filter(Quiz.lesson_id == lesson_id)
            .options(
                joinedload(Quiz.questions).joinedload(Question.options)
            )
            .first()
        )

        return quiz

    except Exception as e:
        print("❌ [get_quiz_by_lesson] Error:", e)
        traceback.print_exc()
        return None
