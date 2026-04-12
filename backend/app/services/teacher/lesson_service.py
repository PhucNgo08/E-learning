from datetime import datetime
from pathlib import Path
from uuid import uuid4
import json

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.quiz import Quiz

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _utcnow() -> datetime:
    return datetime.utcnow()


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_questions_json(questions_json: str | None) -> list[dict]:
    try:
        data = json.loads(questions_json or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _get_owned_module(db: Session, teacher_id: str, module_id: str):
    return (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Module.id == module_id, Course.teacher_id == teacher_id)
        .options(joinedload(Module.course))
        .first()
    )


def _get_owned_lesson(db: Session, teacher_id: str, lesson_id: str, with_module_course: bool = False):
    query = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
    )

    if with_module_course:
        query = query.options(joinedload(Lesson.module).joinedload(Module.course))

    return query.first()


def _save_upload(file_obj, subdir: str):
    upload_dir = BASE_DIR / "uploads" / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4()}_{file_obj.filename}"
    with open(upload_dir / filename, "wb") as f:
        f.write(file_obj.file.read())

    return f"/uploads/{subdir}/{filename}"


def _lesson_has_quiz(db: Session, lesson_id: str) -> bool:
    return db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first() is not None


def _resolve_content_type(has_video: bool, has_document: bool, has_quiz: bool) -> str:
    if has_video and has_document and has_quiz:
        return "mixed"
    if has_quiz and not (has_video or has_document):
        return "quiz"
    if has_video and not has_document and not has_quiz:
        return "video"
    if has_document and not has_video and not has_quiz:
        return "document"
    return "mixed"


def _replace_quiz(db: Session, lesson: Lesson, questions_data: list[dict]):
    old_quizzes = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).all()
    for old_quiz in old_quizzes:
        questions = db.query(Question).filter(Question.quiz_id == old_quiz.id).all()
        for q in questions:
            db.query(QuestionOption).filter(QuestionOption.question_id == q.id).delete()
        db.query(Question).filter(Question.quiz_id == old_quiz.id).delete()
        db.delete(old_quiz)

    if not questions_data:
        return

    quiz = Quiz(
        id=str(uuid4()),
        title=f"Quiz của bài học: {lesson.title}",
        lesson_id=lesson.id,
        course_id=lesson.module.course_id,
        total_questions=len(questions_data),
        status="published",
        is_approved=True,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(quiz)
    db.flush()

    for idx, q in enumerate(questions_data, start=1):
        question_text = (q.get("question") or "").strip()
        if not question_text:
            continue

        question = Question(
            id=str(uuid4()),
            quiz_id=quiz.id,
            question_text=question_text,
            question_order=idx,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(question)
        db.flush()

        options = q.get("options") or []
        correct = q.get("correct")

        for opt_i, opt_text in enumerate(options, start=1):
            clean_option = (opt_text or "").strip()
            if not clean_option:
                continue

            option = QuestionOption(
                id=str(uuid4()),
                question_id=question.id,
                option_text=clean_option,
                is_correct=1 if correct == opt_i else 0,
                option_order=opt_i,
                created_at=_utcnow(),
            )
            db.add(option)


def list_lessons_by_module(db: Session, teacher_id: str, module_id: str):
    module = _get_owned_module(db, teacher_id, module_id)
    if not module:
        return None, []

    lessons = (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )
    return module, lessons


def list_lessons_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .order_by(
            Course.course_name.asc(),
            Module.module_number.asc(),
            Lesson.lesson_number.asc(),
        )
        .all()
    )


def create_lesson(
    db: Session,
    teacher_id: str,
    module_id: str,
    title: str,
    description: str,
    video_url: str,
    document_url: str,
    document_file,
    questions_json: str,
    thumbnail_file,
):
    module = _get_owned_module(db, teacher_id, module_id)
    if not module:
        raise ValueError("Module không thuộc sở hữu của bạn.")

    title = _clean_text(title)
    description = _clean_text(description)
    video_url = _clean_text(video_url)
    document_url = _clean_text(document_url)
    parsed_questions = _parse_questions_json(questions_json)

    if not title:
        raise ValueError("Tiêu đề bài học không được để trống.")

    final_document_url = None
    if document_file and getattr(document_file, "filename", None):
        final_document_url = _save_upload(document_file, "documents")
    elif document_url:
        final_document_url = document_url

    has_video = bool(video_url)
    has_document = bool(final_document_url)
    has_quiz = bool(parsed_questions)

    if not (has_video or has_document or has_quiz):
        raise ValueError("Cần ít nhất 1 nội dung: Video, Tài liệu hoặc Trắc nghiệm.")

    lesson_number = (
        db.query(func.count(Lesson.id))
        .filter(Lesson.module_id == module_id)
        .scalar()
        or 0
    ) + 1

    thumbnail_url = None
    if thumbnail_file and getattr(thumbnail_file, "filename", None):
        thumbnail_url = _save_upload(thumbnail_file, "lessons")

    lesson = Lesson(
        id=str(uuid4()),
        module_id=module_id,
        lesson_number=lesson_number,
        title=title,
        description=description,
        content_type=_resolve_content_type(has_video, has_document, has_quiz),
        video_url=video_url,
        document_url=final_document_url,
        thumbnail_url=thumbnail_url,
        is_published=True,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )

    try:
        db.add(lesson)
        db.flush()

        if parsed_questions:
            _replace_quiz(db, lesson, parsed_questions)

        db.commit()
        db.refresh(lesson)
        return lesson

    except Exception:
        db.rollback()
        raise


def get_lesson_owned(db: Session, teacher_id: str, lesson_id: str, with_module_course: bool = False):
    return _get_owned_lesson(db, teacher_id, lesson_id, with_module_course)


def update_lesson(
    db: Session,
    teacher_id: str,
    lesson_id: str,
    title: str,
    description: str,
    video_url: str,
    document_url: str,
    document_file,
    thumbnail_file,
):
    lesson = _get_owned_lesson(db, teacher_id, lesson_id, with_module_course=True)
    if not lesson:
        raise ValueError("Bài học không tồn tại hoặc bạn không có quyền.")

    title = _clean_text(title)
    description = _clean_text(description)
    video_url = _clean_text(video_url)
    document_url = _clean_text(document_url)

    if not title:
        raise ValueError("Tiêu đề bài học không được để trống.")

    final_document_url = lesson.document_url

    if document_file and getattr(document_file, "filename", None):
        final_document_url = _save_upload(document_file, "documents")
    elif document_url:
        final_document_url = document_url

    has_quiz = _lesson_has_quiz(db, lesson.id)
    has_video = bool(video_url)
    has_document = bool(final_document_url)

    if not (has_video or has_document or has_quiz):
        raise ValueError("Cần ít nhất 1 nội dung: Video, Tài liệu hoặc Trắc nghiệm.")

    lesson.title = title
    lesson.description = description
    lesson.video_url = video_url
    lesson.document_url = final_document_url
    lesson.content_type = _resolve_content_type(has_video, has_document, has_quiz)
    lesson.updated_at = _utcnow()

    if thumbnail_file and getattr(thumbnail_file, "filename", None):
        lesson.thumbnail_url = _save_upload(thumbnail_file, "lessons")

    try:
        db.commit()
        db.refresh(lesson)
        return lesson
    except Exception:
        db.rollback()
        raise


def replace_lesson_quiz(
    db: Session,
    teacher_id: str,
    lesson_id: str,
    questions_json: str,
):
    lesson = _get_owned_lesson(db, teacher_id, lesson_id, with_module_course=True)
    if not lesson:
        raise ValueError("Không tìm thấy bài học hoặc không có quyền sửa quiz.")

    parsed_questions = _parse_questions_json(questions_json)

    try:
        _replace_quiz(db, lesson, parsed_questions)

        has_quiz = bool(parsed_questions)
        has_video = bool(_clean_text(lesson.video_url))
        has_document = bool(_clean_text(lesson.document_url))

        lesson.content_type = _resolve_content_type(has_video, has_document, has_quiz)
        lesson.updated_at = _utcnow()

        db.commit()
        db.refresh(lesson)
        return lesson

    except Exception:
        db.rollback()
        raise


def delete_lesson(db: Session, teacher_id: str, lesson_id: str):
    lesson = _get_owned_lesson(db, teacher_id, lesson_id, with_module_course=True)
    if not lesson:
        raise ValueError("Không thể xoá bài học không thuộc sở hữu của bạn.")

    module_id = lesson.module_id

    try:
        _replace_quiz(db, lesson, [])
        db.delete(lesson)
        db.commit()
        return module_id
    except Exception:
        db.rollback()
        raise