from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.models.course import Course
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.question import Question
from app.services.teacher import lesson_service

router = APIRouter(
    prefix="/teacher/lessons",
    tags=["Teacher - Lessons Management"],
)


@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/teacher/lessons/list-all", status_code=303)


@router.get("/list/{module_id}", response_class=HTMLResponse)
def list_lessons(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    module, lessons = lesson_service.list_lessons_by_module(db, current_teacher.id, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc bạn không có quyền xem.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list.html",
        {
            "request": request,
            "lessons": lessons,
            "module": module,
            "course": module.course,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.get("/list-all", response_class=HTMLResponse)
def list_all_lessons(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    lessons = lesson_service.list_lessons_by_teacher(db, current_teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/list_all.html",
        {
            "request": request,
            "lessons": lessons,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.get("/create", response_class=HTMLResponse)
def create_lesson_general(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    modules = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == current_teacher.id)
        .options(joinedload(Module.course))
        .order_by(Course.course_name.asc(), Module.module_number.asc())
        .all()
    )

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create_general.html",
        {
            "request": request,
            "modules": modules,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.get("/create/{module_id}", response_class=HTMLResponse)
def create_lesson_page(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    module, _ = lesson_service.list_lessons_by_module(db, current_teacher.id, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module hoặc không có quyền tạo bài học.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/create.html",
        {
            "request": request,
            "module": module,
            "course": module.course,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.post("/create/{module_id}")
def create_lesson(
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
    try:
        lesson_service.create_lesson(
            db=db,
            teacher_id=current_teacher.id,
            module_id=module_id,
            title=title,
            description=description,
            video_url=video_url,
            document_url=document_url,
            document_file=document_file,
            questions_json=questions_json,
            thumbnail_file=thumbnail,
        )
        return RedirectResponse(f"/teacher/lessons/list/{module_id}", status_code=303)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo bài học: {e}")


@router.get("/edit/{lesson_id}", response_class=HTMLResponse)
def edit_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    lesson = lesson_service.get_lesson_owned(
        db,
        current_teacher.id,
        lesson_id,
        with_module_course=True,
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học hoặc không có quyền.")

    quizzes = (
        db.query(Quiz)
        .filter(Quiz.lesson_id == lesson.id)
        .options(joinedload(Quiz.questions).joinedload(Question.options))
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
            "teacher_name": current_teacher.full_name,
        },
    )


@router.post("/edit/{lesson_id}")
def edit_lesson(
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
    try:
        lesson = lesson_service.update_lesson(
            db=db,
            teacher_id=current_teacher.id,
            lesson_id=lesson_id,
            title=title,
            description=description,
            video_url=video_url,
            document_url=document_url,
            document_file=document_file,
            thumbnail_file=thumbnail,
        )
        return RedirectResponse(f"/teacher/lessons/edit/{lesson.id}", status_code=303)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi cập nhật bài học: {e}")


@router.post("/edit/{lesson_id}/quiz")
def edit_lesson_quiz(
    lesson_id: str,
    questions_json: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        lesson_service.replace_lesson_quiz(
            db=db,
            teacher_id=current_teacher.id,
            lesson_id=lesson_id,
            questions_json=questions_json,
        )
        return RedirectResponse(f"/teacher/lessons/edit/{lesson_id}", status_code=303)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lưu quiz: {e}")


@router.get("/delete/{lesson_id}", response_class=HTMLResponse)
def delete_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    lesson = lesson_service.get_lesson_owned(
        db,
        current_teacher.id,
        lesson_id,
        with_module_course=True,
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học hoặc không có quyền xoá.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "lessons/delete.html",
        {
            "request": request,
            "lesson": lesson,
            "module": lesson.module,
            "course": lesson.module.course,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.post("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        module_id = lesson_service.delete_lesson(db, current_teacher.id, lesson_id)
        return RedirectResponse(f"/teacher/lessons/list/{module_id}", status_code=303)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xoá bài học: {e}")