import logging
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette import status

from app.config.template_config import templates
from app.database.connection import get_db
from app.services.common.course_access_service import (
    has_course_access,
    get_active_course_enrollment,
)
from app.services.student import lesson_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])


def get_current_student_id(request: Request) -> str | None:
    user_id = request.session.get("user_id")
    role = request.session.get("user_role") or request.session.get("role")
    if not user_id or role != "student":
        return None
    return user_id


def _render_error(request: Request, message: str, status_code: int = 400):
    return templates["student"].TemplateResponse(
        "error.html",
        {
            "request": request,
            "message": message,
            "active_page": "lesson",
        },
        status_code=status_code,
    )


def _student_course_access_flags(
    db: Session,
    user_id: str,
    course_id: str,
) -> tuple[bool, bool, bool]:
    enrollment = get_active_course_enrollment(db, user_id, course_id)
    can_access = enrollment is not None

    if not enrollment:
        return False, False, False

    enrollment_source = (getattr(enrollment, "enrollment_source", None) or "").strip().lower()
    purchased = enrollment_source in {"purchase", "wallet", "order", "paid"}
    enrolled = True

    return can_access, purchased, enrolled


def redirect_need_buy(request: Request, course_id: str) -> RedirectResponse:
    next_url = quote(str(request.url))
    return RedirectResponse(
        url=f"/student/course/detail/{course_id}?need_buy=1&next={next_url}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/", response_class=HTMLResponse)
async def student_lesson_home():
    return RedirectResponse(
        "/student/lesson/module",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/module", response_class=HTMLResponse, name="student_lesson_module_list")
async def list_all_modules(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        modules = lesson_service.get_modules_for_student(db, user_id)

        return templates["student"].TemplateResponse(
            "lesson/module_list.html",
            {
                "request": request,
                "modules": modules,
                "page_title": "Danh sách module",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [list_all_modules] Error: %s", e)
        return HTMLResponse("Lỗi tải danh sách module.", status_code=500)


@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        base_data = lesson_service.get_lessons_by_module(db, module_id, user_id=None)
        if not base_data:
            return _render_error(request, "Không tìm thấy module.", status_code=404)

        module = base_data["module"]
        course = module.course if module else None
        if not module or not course:
            return _render_error(request, "Module không hợp lệ.", status_code=404)

        if not has_course_access(db, user_id, str(course.id)):
            return redirect_need_buy(request, str(course.id))

        data = lesson_service.get_lessons_by_module(db, module_id, user_id=user_id)
        lessons = data.get("lessons", []) if data else base_data.get("lessons", [])

        return templates["student"].TemplateResponse(
            "lesson/module.html",
            {
                "request": request,
                "module": module,
                "course": course,
                "lessons": lessons,
                "page_title": "Chi tiết module",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [list_lessons_in_module] Error: %s", e)
        return HTMLResponse("Lỗi tải module.", status_code=500)


@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return _render_error(request, "Không tìm thấy bài học.", status_code=404)

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return _render_error(request, "Cấu trúc bài học không hợp lệ.", status_code=404)

        is_preview = bool(getattr(lesson, "is_preview", 0))
        can_access, purchased, enrolled = _student_course_access_flags(db, user_id, str(course.id))

        if not is_preview and not can_access:
            return redirect_need_buy(request, str(course.id))

        progress = lesson_service.get_lesson_progress(db, user_id, lesson_id) if can_access else None
        quiz = lesson_service.get_quiz_by_lesson(db, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_view.html",
            {
                "request": request,
                "lesson": lesson,
                "module": module,
                "course": course,
                "progress": progress,
                "quiz": quiz,
                "is_preview": is_preview,
                "purchased": purchased,
                "enrolled": enrolled,
                "page_title": lesson.title,
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [view_lesson] Error: %s", e)
        return HTMLResponse("Lỗi khi mở bài học.", status_code=500)


@router.post("/complete/{lesson_id}", name="student_lesson_mark_complete")
async def mark_lesson_complete(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return HTMLResponse("Bài học không tồn tại.", status_code=404)

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return HTMLResponse("Cấu trúc bài học không hợp lệ.", status_code=404)

        if not has_course_access(db, user_id, str(course.id)):
            return redirect_need_buy(request, str(course.id))

        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)
        if not progress:
            return HTMLResponse("Không thể cập nhật trạng thái bài học.", status_code=400)

        module_data = lesson_service.get_lessons_by_module(db, lesson.module_id, user_id=user_id)
        next_lesson = None
        if module_data and module_data.get("lessons"):
            lessons = module_data["lessons"]
            for idx, item in enumerate(lessons):
                if str(item.id) == str(lesson.id):
                    if idx + 1 < len(lessons):
                        next_lesson = lessons[idx + 1]
                    break

        return templates["student"].TemplateResponse(
            "lesson/lesson_completed.html",
            {
                "request": request,
                "lesson": lesson,
                "module": module,
                "course": course,
                "progress": progress,
                "next_lesson": next_lesson,
                "page_title": "Hoàn thành bài học",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [mark_lesson_complete] Error: %s", e)
        return HTMLResponse("Lỗi đánh dấu hoàn thành.", status_code=500)


@router.get("/notes/add/{lesson_id}", response_class=HTMLResponse, name="student_lesson_add_note")
async def add_lesson_note_form(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return _render_error(request, "Không tìm thấy bài học.", status_code=404)

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return _render_error(request, "Cấu trúc bài học không hợp lệ.", status_code=404)

        if not has_course_access(db, user_id, str(course.id)):
            return redirect_need_buy(request, str(course.id))

        return templates["student"].TemplateResponse(
            "lesson/note_form.html",
            {
                "request": request,
                "lesson": lesson,
                "page_title": "Thêm ghi chú",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [add_lesson_note_form] Error: %s", e)
        return HTMLResponse("Lỗi mở form thêm ghi chú.", status_code=500)


@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return _render_error(request, "Không tìm thấy bài học.", status_code=404)

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return _render_error(request, "Cấu trúc bài học không hợp lệ.", status_code=404)

        if not has_course_access(db, user_id, str(course.id)):
            return redirect_need_buy(request, str(course.id))

        notes = lesson_service.get_notes_by_lesson(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_notes.html",
            {
                "request": request,
                "lesson": lesson,
                "notes": notes,
                "page_title": "Ghi chú bài học",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [view_lesson_notes] Error: %s", e)
        return HTMLResponse("Lỗi tải ghi chú.", status_code=500)


@router.post("/notes/{lesson_id}", name="student_lesson_save_note")
async def save_lesson_note(
    request: Request,
    lesson_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return JSONResponse(
            {"status": "error", "message": "Bạn chưa đăng nhập."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return JSONResponse(
                {"status": "error", "message": "Bài học không tồn tại."},
                status_code=404,
            )

        module = lesson.module
        course = module.course if module else None
        if not module or not course:
            return JSONResponse(
                {"status": "error", "message": "Cấu trúc bài học không hợp lệ."},
                status_code=404,
            )

        if not has_course_access(db, user_id, str(course.id)):
            return JSONResponse(
                {"status": "error", "message": "Bạn không có quyền ghi chú cho bài học này."},
                status_code=403,
            )

        note = lesson_service.add_note_to_lesson(db, user_id, lesson_id, content)
        if not note:
            return JSONResponse(
                {"status": "error", "message": "Không thể lưu ghi chú."},
                status_code=400,
            )

        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.exception("❌ [save_lesson_note] Error: %s", e)
        return JSONResponse(
            {"status": "error", "message": "Lỗi hệ thống."},
            status_code=500,
        )


@router.get("/progress", response_class=HTMLResponse, name="student_lesson_progress")
async def view_learning_progress(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_student_id(request)
    if not user_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        progress_data = lesson_service.get_learning_progress(db, user_id)

        return templates["student"].TemplateResponse(
            "lesson/progress.html",
            {
                "request": request,
                "progress_data": progress_data,
                "page_title": "Tiến độ học tập",
                "active_page": "lesson",
            },
        )
    except Exception as e:
        logger.exception("❌ [view_learning_progress] Error: %s", e)
        return HTMLResponse("Lỗi khi tải tiến độ.", status_code=500)


@router.post("/check-answer")
async def check_answer(
    request: Request,
    question_id: str = Form(...),
    option_id: str = Form(...),
    db: Session = Depends(get_db),
):
    user_id = get_current_student_id(request)
    if not user_id:
        return JSONResponse(
            {"status": "error", "message": "Bạn chưa đăng nhập."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        from app.models.question import Question
        from app.models.question_option import QuestionOption
        from app.models.quiz import Quiz

        row = (
            db.query(QuestionOption, Question, Quiz)
            .join(Question, QuestionOption.question_id == Question.id)
            .join(Quiz, Question.quiz_id == Quiz.id)
            .filter(
                QuestionOption.id == option_id,
                QuestionOption.question_id == question_id,
            )
            .first()
        )

        if not row:
            return JSONResponse(
                {"status": "error", "message": "Không tìm thấy lựa chọn."},
                status_code=404,
            )

        option, question, quiz = row

        course_id = str(quiz.course_id) if getattr(quiz, "course_id", None) else None
        lesson_id = str(quiz.lesson_id) if getattr(quiz, "lesson_id", None) else None
        is_preview = False

        if lesson_id:
            lesson = lesson_service.get_lesson_detail(db, lesson_id)
            if lesson and lesson.module and lesson.module.course:
                course_id = str(lesson.module.course.id)
                is_preview = bool(getattr(lesson, "is_preview", 0))

        if course_id and not is_preview and not has_course_access(db, user_id, course_id):
            return JSONResponse(
                {"status": "error", "message": "Bạn không có quyền xem đáp án của nội dung này."},
                status_code=403,
            )

        return JSONResponse({"status": "ok", "correct": bool(option.is_correct)})
    except Exception as e:
        logger.exception("❌ [check_answer] Error: %s", e)
        return JSONResponse(
            {"status": "error", "message": "Lỗi xử lý."},
            status_code=500,
        )