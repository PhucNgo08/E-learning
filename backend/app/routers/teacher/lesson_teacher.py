from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException,
    UploadFile, File
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import json

# Internal imports
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/lessons",
    tags=["Teacher - Lessons Management"]
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


# =============================================================
# REDIRECT ROOT
# =============================================================
@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/teacher/lessons/list-all", status_code=303)


# =============================================================
# 1. LIST LESSONS IN MODULE
# =============================================================
@router.get("/list/{module_id}", response_class=HTMLResponse)
def list_lessons(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id
    module = db.query(Module).filter(Module.id == module_id).first()

    if not module:
        raise HTTPException(404, "Không tìm thấy module.")

    course = db.query(Course).filter(
        Course.id == module.course_id,
        Course.teacher_id == teacher_id
    ).first()

    if not course:
        raise HTTPException(403, "Bạn không có quyền xem module này.")

    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id
    ).order_by(Lesson.lesson_number.asc()).all()

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list.html",
        {
            "request": request,
            "lessons": lessons,
            "module": module,
            "course": course,
            "teacher_name": current_teacher.full_name
        }
    )


# =============================================================
# 2. LIST ALL LESSONS BY TEACHER
# =============================================================
@router.get("/list-all", response_class=HTMLResponse)
def list_all_lessons(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id

    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(
            Course.course_name.asc(),
            Module.module_number.asc(),
            Lesson.lesson_number.asc()
        )
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list_all.html",
        {"request": request, "lessons": lessons, "teacher_name": current_teacher.full_name}
    )


# =============================================================
# 3. CREATE PAGE GENERAL
# =============================================================
@router.get("/create", response_class=HTMLResponse)
def create_lesson_general(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id

    modules = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc(), Module.module_number.asc())
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create_general.html",
        {"request": request, "modules": modules, "teacher_name": current_teacher.full_name}
    )


# =============================================================
# 3.1 CREATE PAGE PER MODULE
# =============================================================
@router.get("/create/{module_id}", response_class=HTMLResponse)
def create_lesson_page(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    teacher_id = current_teacher.id

    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(404, "Không tìm thấy module.")

    course = db.query(Course).filter(
        Course.id == module.course_id,
        Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(403, "Bạn không có quyền tạo bài học.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create.html",
        {
            "request": request,
            "module": module,
            "course": course,
            "teacher_name": current_teacher.full_name
        }
    )


# =============================================================
# 3.2 CREATE POST (FULL VIDEO + FILE + QUIZ)
# =============================================================
@router.post("/create/{module_id}")
async def create_lesson(
    module_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),

    title: str = Form(...),
    description: str = Form(""),

    video_url: str = Form(""),

    document_url: str = Form(""),
    document_file: UploadFile | None = File(None),

    questions_json: str = Form("[]"),

    thumbnail: UploadFile | None = File(None),
):
    teacher_id = current_teacher.id

    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(404, "Module không tồn tại.")

    course = db.query(Course).filter(
        Course.id == module.course_id,
        Course.teacher_id == teacher_id
    ).first()
    if not course:
        raise HTTPException(403, "Không có quyền.")

    # DOCUMENT
    document_file_path = None
    if document_file and document_file.filename:
        upload_dir = BASE_DIR / "uploads/documents"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4()}_{document_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(await document_file.read())
        document_file_path = f"/uploads/documents/{filename}"

    final_document = document_file_path or (document_url.strip() or None)

    # VALIDATE
    if not (video_url.strip() or final_document or questions_json not in ["", "[]"]):
        raise HTTPException(400, "Cần ít nhất 1 nội dung.")

    # AUTO NUMBER
    next_number = db.query(Lesson).filter(
        Lesson.module_id == module_id
    ).count() + 1

    # THUMBNAIL
    thumbnail_path = None
    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "uploads/lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}_{thumbnail.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(await thumbnail.read())
        thumbnail_path = f"/uploads/lessons/{filename}"

    # CREATE LESSON
    lesson = Lesson(
        id=str(uuid4()),
        module_id=module_id,
        lesson_number=next_number,
        title=title,
        description=description,
        content_type="mixed",
        video_url=video_url.strip() or None,
        document_url=final_document,
        thumbnail_url=thumbnail_path,
        is_published=True,
        created_at=datetime.utcnow(),
    )

    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    # QUIZ SAVE
    try:
        data = json.loads(questions_json)
    except:
        data = []

    if len(data) > 0:
        quiz = Quiz(
            id=str(uuid4()),
            title=f"Quiz: {lesson.title}",
            lesson_id=lesson.id,
            course_id=course.id,
            total_questions=len(data),
            created_at=datetime.utcnow()
        )
        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        # Save each question
        for idx, q in enumerate(data, start=1):
            question = Question(
                id=str(uuid4()),
                quiz_id=quiz.id,
                question_text=q["question"],
                question_order=idx
            )
            db.add(question)
            db.commit()
            db.refresh(question)

            # OPTIONS
            for opt_i, opt_text in enumerate(q["options"], start=1):
                option = QuestionOption(
                    id=str(uuid4()),
                    question_id=question.id,
                    option_text=opt_text,
                    is_correct=1 if q["correct"] == opt_i else 0,
                    option_order=opt_i
                )
                db.add(option)

        db.commit()

    return RedirectResponse(f"/teacher/lessons/list/{module_id}", 303)


# =============================================================
# 4. EDIT PAGE (ĐÃ FIX 100%)
# =============================================================
@router.get("/edit/{lesson_id}", response_class=HTMLResponse)
def edit_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    # Load lesson + module + course
    lesson = (
        db.query(Lesson)
        .options(
            joinedload(Lesson.module).joinedload(Module.course)
        )
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(403, "Không có quyền chỉnh sửa bài học.")

    # Load QUÍZ đúng cách
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.lesson_id == lesson.id)
        .options(
            joinedload(Quiz.questions).joinedload(Question.options)
        )
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/edit.html",
        {
            "request": request,
            "lesson": lesson,
            "module": lesson.module,
            "course": lesson.module.course,
            "quizzes": quizzes,
            "teacher_name": current_teacher.full_name
        }
    )



# =============================================================
# 4.2 EDIT CONTENT POST
# =============================================================
@router.post("/edit/{lesson_id}")
async def edit_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),

    title: str = Form(...),
    description: str = Form(""),

    video_url: str = Form(""),
    document_url: str = Form(""),
    document_file: UploadFile | None = File(None),

    thumbnail: UploadFile | None = File(None),
):
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(403, "Không có quyền sửa.")

    # DOCUMENT
    document_file_path = None
    if document_file and document_file.filename:
        upload_dir = BASE_DIR / "uploads/documents"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}_{document_file.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(await document_file.read())
        document_file_path = f"/uploads/documents/{filename}"

    final_doc = document_file_path or (document_url.strip() or lesson.document_url)

    if not (video_url.strip() or final_doc):
        raise HTTPException(400, "Cần ít nhất 1 nội dung.")

    # UPDATE
    lesson.title = title
    lesson.description = description
    lesson.video_url = video_url.strip() or None
    lesson.document_url = final_doc
    lesson.updated_at = datetime.utcnow()

    # THUMBNAIL
    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "uploads/lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}_{thumbnail.filename}"
        with open(upload_dir / filename, "wb") as f:
            f.write(await thumbnail.read())
        lesson.thumbnail_url = f"/uploads/lessons/{filename}"

    db.commit()
    db.refresh(lesson)

    return RedirectResponse(f"/teacher/lessons/edit/{lesson_id}", 303)


# =============================================================
# 4.3 EDIT QUIZ POST
# =============================================================
@router.post("/edit/{lesson_id}/quiz")
async def edit_lesson_quiz(
    lesson_id: str,
    questions_json: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(403, "Không có quyền sửa quiz.")

    # XOÁ QUIZ CŨ
    old_quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if old_quiz:
        db.delete(old_quiz)
        db.commit()

    data = json.loads(questions_json)

    if len(data) == 0:
        return RedirectResponse(f"/teacher/lessons/edit/{lesson_id}", 303)

    # TẠO QUIZ MỚI
    quiz = Quiz(
        id=str(uuid4()),
        title=f"Quiz của bài học: {lesson.title}",
        lesson_id=lesson.id,
        course_id=lesson.module.course.id,
        total_questions=len(data),
        created_at=datetime.utcnow()
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    # TẠO CÂU HỎI & ĐÁP ÁN
    for idx, q in enumerate(data, start=1):
        question = Question(
            id=str(uuid4()),
            quiz_id=quiz.id,
            question_text=q["question"],
            question_order=idx
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        for opt_i, opt_text in enumerate(q["options"], start=1):
            option = QuestionOption(
                id=str(uuid4()),
                question_id=question.id,
                option_text=opt_text,
                is_correct=1 if q["correct"] == opt_i else 0,
                option_order=opt_i
            )
            db.add(option)

    db.commit()

    return RedirectResponse(f"/teacher/lessons/edit/{lesson_id}", 303)


# =============================================================
# 5. DELETE PAGE
# =============================================================
@router.get("/delete/{lesson_id}", response_class=HTMLResponse)
def delete_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.module).joinedload(Module.course))
        .filter(Lesson.id == lesson_id)
        .first()
    )

    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học.")

    if lesson.module.course.teacher_id != current_teacher.id:
        raise HTTPException(403, "Không có quyền xoá.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/delete.html",
        {
            "request": request,
            "lesson": lesson,
            "module": lesson.module,
            "course": lesson.module.course,
            "teacher_name": current_teacher.full_name
        }
    )


# =============================================================
# 6. DELETE POST
# =============================================================
@router.post("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(404, "Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    if module.course.teacher_id != current_teacher.id:
        raise HTTPException(403, "Không có quyền xoá.")

    module_id = lesson.module_id

    db.delete(lesson)
    db.commit()

    return RedirectResponse(f"/teacher/lessons/list/{module_id}", 303)
