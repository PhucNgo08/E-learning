from sqlalchemy.orm import Session, joinedload
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.course import Course
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent.parent.parent


# =========================================================
# 📋 1️⃣ Danh sách bài học theo module
# =========================================================
def list_lessons_by_module(db: Session, module_id: str):
    return (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )


# =========================================================
# 📋 2️⃣ Danh sách tất cả bài học của giáo viên
# =========================================================
def list_lessons_by_teacher(db: Session, teacher_id: str):
    return (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .order_by(Lesson.created_at.desc())
        .all()
    )


# =========================================================
# ➕ 3️⃣ Tạo bài học (VIDEO + FILE + LINK + QUIZ)
# =========================================================
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
    # -------------------- 1) Validate quyền module --------------------
    module = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Module.id == module_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not module:
        raise ValueError("Module không thuộc sở hữu của bạn.")

    # ======================================================
    # 2) Xử lý tài liệu (ưu tiên file)
    # ======================================================
    final_document_url = None

    # File upload
    if document_file and document_file.filename:
        upload_dir = BASE_DIR / "uploads" / "documents"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{document_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(document_file.file.read())

        final_document_url = f"/uploads/documents/{filename}"

    # Link
    elif document_url.strip():
        final_document_url = document_url.strip()

    # ======================================================
    # 3) Validate nội dung
    # ======================================================
    if not (video_url.strip() or final_document_url or questions_json not in ["", "[]"]):
        raise ValueError("Cần ít nhất 1 nội dung: Video, Tài liệu hoặc Trắc nghiệm.")

    # ======================================================
    # 4) Auto number
    # ======================================================
    lesson_number = (
        db.query(Lesson).filter(Lesson.module_id == module_id).count() + 1
    )

    # ======================================================
    # 5) Thumbnail
    # ======================================================
    thumbnail_url = None

    if thumbnail_file and thumbnail_file.filename:
        upload_dir = BASE_DIR / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{thumbnail_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(thumbnail_file.file.read())

        thumbnail_url = f"/uploads/lessons/{filename}"

    # ======================================================
    # 6) Create Lesson
    # ======================================================
    lesson = Lesson(
        id=str(uuid4()),
        module_id=module_id,
        lesson_number=lesson_number,
        title=title.strip(),
        description=description.strip(),
        content_type="mixed",
        video_url=video_url.strip() or None,
        document_url=final_document_url,
        thumbnail_url=thumbnail_url,
        is_published=True,
        created_at=datetime.now(),
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    # ======================================================
    # 7) Save Quiz Nếu Có
    # ======================================================
    try:
        questions = json.loads(questions_json)
    except:
        questions = []

    if len(questions) > 0:

        quiz = Quiz(
            id=str(uuid4()),
            title=f"Quiz của bài học: {lesson.title}",
            lesson_id=lesson.id,             # 🔥 QUAN TRỌNG
            course_id=module.course_id,
            total_questions=len(questions),
            created_at=datetime.now(),
        )

        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        # Save Questions
        for idx, q in enumerate(questions, start=1):
            question = Question(
                id=str(uuid4()),
                quiz_id=quiz.id,
                question_text=q["question"],
                question_order=idx,
                created_at=datetime.now(),
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            # Save Options
            for i, opt in enumerate(q["options"], start=1):
                option = QuestionOption(
                    id=str(uuid4()),
                    question_id=question.id,
                    option_text=opt,
                    is_correct=1 if q["correct"] == i else 0,
                    option_order=i
                )
                db.add(option)

        db.commit()

    return lesson


# =========================================================
# ✏️ 4️⃣ Lấy bài học theo quyền giáo viên
# =========================================================
def get_lesson_owned(db: Session, teacher_id: str, lesson_id: str, with_module_course=False):

    query = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
    )

    if with_module_course:
        query = query.options(
            joinedload(Lesson.module).joinedload(Module.course)
        )

    return query.first()


# =========================================================
# ✏️ 5️⃣ Cập nhật bài học (VIDEO + FILE + LINK)
# =========================================================
def update_lesson(
    db: Session,
    teacher_id: str,
    lesson_id: str,
    title: str,
    description: str,
    video_url: str,
    document_url: str,
    document_file,
    thumbnail_file
):
    # Load lesson
    lesson = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson:
        raise ValueError("Bài học không tồn tại hoặc bạn không có quyền.")

    # ================= DOCUMENT =================
    final_document_url = lesson.document_url

    if document_file and document_file.filename:
        upload_dir = BASE_DIR / "uploads" / "documents"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{document_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(document_file.file.read())

        final_document_url = f"/uploads/documents/{filename}"

    elif document_url.strip():
        final_document_url = document_url.strip()

    # Validate
    if not (video_url.strip() or final_document_url):
        raise ValueError("Cần ít nhất 1 nội dung (Video hoặc Tài liệu).")

    # Update core fields
    lesson.title = title.strip()
    lesson.description = description.strip()
    lesson.video_url = video_url.strip() or None
    lesson.document_url = final_document_url
    lesson.updated_at = datetime.now()

    # Update thumbnail
    if thumbnail_file and thumbnail_file.filename:
        upload_dir = BASE_DIR / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{thumbnail_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(thumbnail_file.file.read())

        lesson.thumbnail_url = f"/uploads/lessons/{filename}"

    db.commit()
    db.refresh(lesson)

    return lesson.module_id


# =========================================================
# ❌ 6️⃣ Xoá bài học
# =========================================================
def delete_lesson(db: Session, teacher_id: str, lesson_id: str):

    lesson = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Lesson.id == lesson_id, Course.teacher_id == teacher_id)
        .first()
    )

    if not lesson:
        raise ValueError("Không thể xoá bài học không thuộc sở hữu của bạn.")

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()

    return module_id
