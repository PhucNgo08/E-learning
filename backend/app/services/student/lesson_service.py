from datetime import datetime
import logging
import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.learning_activity_log import LearningActivityLog
from app.models.lesson import Lesson
from app.models.lesson_note import LessonNote
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.models.student_profile import StudentProfile
from app.services.common.course_access_service import (
    get_accessible_course_ids,
    has_course_access,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.utcnow()


def _get_lesson_with_structure(db: Session, lesson_id: str):
    return (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(
            Lesson.id == lesson_id,
            Lesson.is_published == 1,
        )
        .first()
    )


def _get_module_with_course(db: Session, module_id: str):
    return (
        db.query(Module)
        .options(joinedload(Module.course))
        .filter(Module.id == module_id)
        .first()
    )


def _log_learning_activity(
    db: Session,
    *,
    user_id: str,
    activity_type: str,
    course_id: str | None = None,
    module_id: str | None = None,
    lesson_id: str | None = None,
    progress_before: int = 0,
    progress_after: int = 0,
    position_seconds: int = 0,
    duration_seconds: int = 0,
    device_type: str | None = None,
    ip_address: str | None = None,
    metadata_json: dict | None = None,
):
    log = LearningActivityLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        lesson_id=lesson_id,
        activity_type=activity_type,
        progress_before=progress_before,
        progress_after=progress_after,
        position_seconds=position_seconds,
        duration_seconds=duration_seconds,
        device_type=device_type,
        ip_address=ip_address,
        metadata_json=metadata_json,
    )
    db.add(log)
    return log


def _recalculate_course_progress(db: Session, user_id: str, course_id: str):
    total_lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .filter(
            Module.course_id == course_id,
            Lesson.is_published == 1,
        )
        .count()
    )

    completed_lessons = (
        db.query(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Lesson.module_id == Module.id)
        .filter(
            Module.course_id == course_id,
            Lesson.is_published == 1,
            LessonProgress.user_id == user_id,
            LessonProgress.progress_status == "completed",
        )
        .count()
    )

    progress_percent = round((completed_lessons / total_lessons) * 100, 2) if total_lessons > 0 else 0
    now = _now()

    status = "not_started"
    if total_lessons > 0 and completed_lessons == total_lessons:
        status = "completed"
    elif completed_lessons > 0:
        status = "in_progress"

    progress = (
        db.query(CourseProgress)
        .filter(
            CourseProgress.user_id == user_id,
            CourseProgress.course_id == course_id,
        )
        .first()
    )

    if not progress:
        progress = CourseProgress(
            id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            progress_percent=progress_percent,
            completed_lessons=completed_lessons,
            total_lessons=total_lessons,
            status=status,
            started_at=now if completed_lessons > 0 else None,
            completed_at=now if status == "completed" else None,
            created_at=now,
            updated_at=now,
        )
        db.add(progress)
    else:
        progress.progress_percent = progress_percent
        progress.completed_lessons = completed_lessons
        progress.total_lessons = total_lessons
        progress.status = status

        if completed_lessons > 0 and not getattr(progress, "started_at", None):
            progress.started_at = now

        progress.completed_at = now if status == "completed" else None
        progress.updated_at = now

    return progress


def get_lesson_detail(db: Session, lesson_id: str):
    try:
        return _get_lesson_with_structure(db, lesson_id)
    except Exception as e:
        logger.exception("❌ [get_lesson_detail] Error: %s", e)
        return None


def get_lessons_by_module(db: Session, module_id: str, user_id: str | None = None):
    try:
        module = _get_module_with_course(db, module_id)
        if not module or not module.course:
            return None

        if user_id and not has_course_access(db, user_id, module.course_id):
            return None

        lessons = (
            db.query(Lesson)
            .filter(
                Lesson.module_id == module_id,
                Lesson.is_published == 1,
            )
            .order_by(Lesson.lesson_number.asc())
            .all()
        )

        progress_map = {}
        if user_id and lessons:
            lesson_ids = [lesson.id for lesson in lessons]
            progresses = (
                db.query(LessonProgress)
                .filter(
                    LessonProgress.user_id == user_id,
                    LessonProgress.lesson_id.in_(lesson_ids),
                )
                .all()
            )
            progress_map = {p.lesson_id: p for p in progresses}

        for lesson in lessons:
            lesson.progress = progress_map.get(lesson.id)

        return {"module": module, "lessons": lessons}

    except Exception as e:
        logger.exception("❌ [get_lessons_by_module] Error: %s", e)
        return None


def get_modules_by_course(db: Session, course_id: str, user_id: str | None = None):
    try:
        if user_id and not has_course_access(db, user_id, course_id):
            return []

        return (
            db.query(Module)
            .filter(Module.course_id == course_id)
            .order_by(Module.module_number.asc())
            .all()
        )

    except Exception as e:
        logger.exception("❌ [get_modules_by_course] Error: %s", e)
        return []


def get_lesson_progress(db: Session, user_id: str, lesson_id: str):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson or not lesson.module:
            return None

        if not has_course_access(db, user_id, lesson.module.course_id):
            return None

        return (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
            .first()
        )

    except Exception as e:
        logger.exception("❌ [get_lesson_progress] Error: %s", e)
        return None


def mark_lesson_completed(db: Session, user_id: str, lesson_id: str):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson:
            raise ValueError("Không tìm thấy bài học.")

        module = lesson.module
        if not module or not has_course_access(db, user_id, module.course_id):
            raise ValueError("Bạn không có quyền truy cập bài học này.")

        progress = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
            .first()
        )

        now = _now()
        before_percent = 0

        if not progress:
            progress = LessonProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_id=lesson_id,
                progress_status="completed",
                completion_percentage=100,
                time_spent_seconds=0,
                last_position_seconds=0,
                started_at=now,
                completed_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(progress)
        else:
            before_percent = int(progress.completion_percentage or 0)
            progress.progress_status = "completed"
            progress.completion_percentage = 100
            if not getattr(progress, "started_at", None):
                progress.started_at = now
            progress.completed_at = now
            progress.updated_at = now

        _recalculate_course_progress(db, user_id, module.course_id)

        _log_learning_activity(
            db,
            user_id=user_id,
            course_id=module.course_id,
            module_id=module.id,
            lesson_id=lesson_id,
            activity_type="lesson_completed",
            progress_before=before_percent,
            progress_after=100,
            position_seconds=int(progress.last_position_seconds or 0),
            duration_seconds=0,
            metadata_json={"lesson_title": lesson.title},
        )

        db.commit()
        db.refresh(progress)
        return progress

    except Exception as e:
        db.rollback()
        logger.exception("❌ [mark_lesson_completed] Error: %s", e)
        return None


def get_notes_by_lesson(db: Session, user_id: str, lesson_id: str):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson or not lesson.module:
            return []

        if not has_course_access(db, user_id, lesson.module.course_id):
            return []

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
        logger.exception("❌ [get_notes_by_lesson] Error: %s", e)
        return []


def add_note_to_lesson(db: Session, user_id: str, lesson_id: str, content: str):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson:
            raise ValueError("Không tìm thấy bài học.")

        module = lesson.module
        if not module or not has_course_access(db, user_id, module.course_id):
            raise ValueError("Bạn không có quyền ghi chú cho bài học này.")

        clean = (content or "").strip()
        if not clean:
            raise ValueError("Nội dung ghi chú không được để trống.")

        now = _now()
        note = LessonNote(
            id=str(uuid.uuid4()),
            user_id=user_id,
            lesson_id=lesson_id,
            content=clean,
            created_at=now,
            updated_at=now,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    except Exception as e:
        db.rollback()
        logger.exception("❌ [add_note_to_lesson] Error: %s", e)
        return None


def get_modules_for_student(db: Session, user_id: str):
    try:
        course_ids = get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        return (
            db.query(Module)
            .options(joinedload(Module.course))
            .filter(Module.course_id.in_(course_ids))
            .order_by(Module.created_at.desc(), Module.module_number.asc())
            .all()
        )

    except Exception as e:
        logger.exception("❌ [get_modules_for_student] Error: %s", e)
        return []


def get_learning_progress(db: Session, user_id: str):
    try:
        course_ids = get_accessible_course_ids(db, user_id)
        if not course_ids:
            return []

        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        progress_list = []

        for course in courses:
            total_lessons = (
                db.query(Lesson)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    Module.course_id == course.id,
                    Lesson.is_published == 1,
                )
                .count()
            )

            completed_lessons = (
                db.query(LessonProgress)
                .join(Lesson, Lesson.id == LessonProgress.lesson_id)
                .join(Module, Lesson.module_id == Module.id)
                .filter(
                    Module.course_id == course.id,
                    Lesson.is_published == 1,
                    LessonProgress.user_id == user_id,
                    LessonProgress.progress_status == "completed",
                )
                .count()
            )

            completion_rate = round((completed_lessons / total_lessons) * 100, 2) if total_lessons > 0 else 0

            progress_list.append(
                {
                    "course": course,
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_lessons,
                    "completion_rate": completion_rate,
                }
            )

        return progress_list

    except Exception as e:
        logger.exception("❌ [get_learning_progress] Error: %s", e)
        return []


def get_lesson_full_structure(db: Session, lesson_id: str):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson:
            return None

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return None

        return {"lesson": lesson, "module": module, "course": course}

    except Exception as e:
        logger.exception("❌ [get_lesson_full_structure] Error: %s", e)
        return None


def get_quiz_by_lesson(db: Session, lesson_id: str):
    try:
        from app.models.question import Question
        from app.models.question_option import QuestionOption
        from app.models.quiz import Quiz

        quiz = (
            db.query(Quiz)
            .filter(
                Quiz.lesson_id == lesson_id,
                Quiz.status == "published",
            )
            .first()
        )
        if not quiz:
            return None

        questions = (
            db.query(Question)
            .filter(Question.quiz_id == quiz.id)
            .order_by(Question.question_order.asc())
            .all()
        )

        for q in questions:
            q.options = (
                db.query(QuestionOption)
                .filter(QuestionOption.question_id == q.id)
                .order_by(QuestionOption.option_order.asc())
                .all()
            )

        quiz.questions = questions
        return quiz

    except Exception as e:
        logger.exception("❌ [get_quiz_by_lesson] Error: %s", e)
        return None


def save_lesson_progress(
    db: Session,
    user_id: str,
    lesson_id: str,
    position_seconds: int = 0,
    completion_percentage: int = 0,
    duration_seconds: int = 0,
):
    try:
        lesson = _get_lesson_with_structure(db, lesson_id)
        if not lesson:
            raise ValueError("Không tìm thấy bài học.")

        module = lesson.module
        if not module or not has_course_access(db, user_id, module.course_id):
            raise ValueError("Bạn không có quyền truy cập bài học này.")

        progress = (
            db.query(LessonProgress)
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == lesson_id,
            )
            .first()
        )

        now = _now()
        completion_percentage = max(0, min(100, int(completion_percentage or 0)))
        position_seconds = max(0, int(position_seconds or 0))
        duration_seconds = max(0, int(duration_seconds or 0))
        before_percent = 0

        if not progress:
            progress = LessonProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                lesson_id=lesson_id,
                progress_status="completed" if completion_percentage >= 100 else "in_progress",
                completion_percentage=completion_percentage,
                time_spent_seconds=duration_seconds,
                last_position_seconds=position_seconds,
                started_at=now,
                completed_at=now if completion_percentage >= 100 else None,
                created_at=now,
                updated_at=now,
            )
            db.add(progress)
        else:
            before_percent = int(progress.completion_percentage or 0)
            progress.completion_percentage = max(int(progress.completion_percentage or 0), completion_percentage)
            progress.last_position_seconds = position_seconds
            progress.time_spent_seconds = int(progress.time_spent_seconds or 0) + duration_seconds
            progress.progress_status = "completed" if progress.completion_percentage >= 100 else "in_progress"

            if not getattr(progress, "started_at", None):
                progress.started_at = now

            if progress.completion_percentage >= 100:
                progress.completed_at = now

            progress.updated_at = now

        student_profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == user_id)
            .first()
        )
        if student_profile:
            student_profile.total_learning_time = int(student_profile.total_learning_time or 0) + duration_seconds
            student_profile.updated_at = now

        _recalculate_course_progress(db, user_id, module.course_id)

        _log_learning_activity(
            db,
            user_id=user_id,
            course_id=module.course_id,
            module_id=module.id,
            lesson_id=lesson_id,
            activity_type="lesson_progressed",
            progress_before=before_percent,
            progress_after=int(progress.completion_percentage or 0),
            position_seconds=position_seconds,
            duration_seconds=duration_seconds,
            metadata_json={"lesson_title": lesson.title},
        )

        db.commit()
        db.refresh(progress)
        return progress

    except Exception as e:
        db.rollback()
        logger.exception("❌ [save_lesson_progress] Error: %s", e)
        return None


def get_continue_learning(db: Session, user_id: str):
    try:
        accessible_course_ids = get_accessible_course_ids(db, user_id)
        if not accessible_course_ids:
            return None

        progress = (
            db.query(LessonProgress)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Module, Lesson.module_id == Module.id)
            .options(
                joinedload(LessonProgress.lesson)
                .joinedload(Lesson.module)
                .joinedload(Module.course)
            )
            .filter(
                LessonProgress.user_id == user_id,
                LessonProgress.progress_status == "in_progress",
                Lesson.is_published == 1,
                Module.course_id.in_(accessible_course_ids),
            )
            .order_by(LessonProgress.updated_at.desc())
            .first()
        )
        return progress

    except Exception as e:
        logger.exception("❌ [get_continue_learning] Error: %s", e)
        return None


def get_learning_history(db: Session, user_id: str, limit: int = 20):
    try:
        safe_limit = max(1, min(100, int(limit or 20)))

        return (
            db.query(LearningActivityLog)
            .options(
                joinedload(LearningActivityLog.lesson),
                joinedload(LearningActivityLog.module),
                joinedload(LearningActivityLog.course),
            )
            .filter(LearningActivityLog.user_id == user_id)
            .order_by(LearningActivityLog.created_at.desc())
            .limit(safe_limit)
            .all()
        )

    except Exception as e:
        logger.exception("❌ [get_learning_history] Error: %s", e)
        return []


def get_course_progress_records(db: Session, user_id: str):
    try:
        accessible_course_ids = get_accessible_course_ids(db, user_id)
        if not accessible_course_ids:
            return []

        return (
            db.query(CourseProgress)
            .options(joinedload(CourseProgress.course))
            .filter(
                CourseProgress.user_id == user_id,
                CourseProgress.course_id.in_(accessible_course_ids),
            )
            .order_by(CourseProgress.updated_at.desc())
            .all()
        )

    except Exception as e:
        logger.exception("❌ [get_course_progress_records] Error: %s", e)
        return []