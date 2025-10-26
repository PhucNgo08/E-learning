"""
==========================================================
🎓 ROUTER: Student - Lesson
Xử lý các chức năng xem bài học và module của học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from datetime import datetime
import uuid

# ✅ Import cấu hình DB & template
from app.database.connection import get_db
from app.config.template_config import templates

# ✅ Import service & models
from app.services.student import lesson_service
from app.models.lesson_note import LessonNote


# =====================================================
# ⚙️ Cấu hình Router
# =====================================================
router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])


# =====================================================
# 🏠 0️⃣ Trang mặc định /student/lesson
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def student_lesson_home():
    """
    Khi truy cập /student/lesson → tự động chuyển hướng sang /student/lesson/module
    """
    return RedirectResponse(url="/student/lesson/module", status_code=303)


# =====================================================
# 📘 1️⃣ Danh sách tất cả module mà sinh viên đang học
# =====================================================
@router.get("/module", response_class=HTMLResponse, name="student_lesson_module_list")
async def list_all_modules(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị tất cả module mà học viên đã ghi danh
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    modules = lesson_service.get_modules_for_student(db, user_id)
    if not modules:
        return HTMLResponse("<h4>Bạn chưa tham gia khóa học hoặc chưa có module nào.</h4>", status_code=200)

    return templates["student"].TemplateResponse(
        "lesson/module_list.html",
        {
            "request": request,
            "modules": modules,
            "active_page": "lesson",
        },
    )


# =====================================================
# 📗 2️⃣ Danh sách bài học trong 1 module
# =====================================================
@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):
    """Hiển thị danh sách bài học thuộc 1 module"""
    data = lesson_service.get_lessons_by_module(db, module_id)
    if not data:
        return HTMLResponse("<h4>Không tìm thấy module hoặc bài học.</h4>", status_code=404)

    module = data["module"]
    lessons = data["lessons"]

    return templates["student"].TemplateResponse(
        "lesson/module.html",
        {
            "request": request,
            "module": module,
            "lessons": lessons,
            "active_page": "lesson",
        },
    )


# =====================================================
# 📕 3️⃣ Xem chi tiết 1 bài học
# =====================================================
@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị chi tiết nội dung của 1 bài học"""
    lesson = lesson_service.get_lesson_detail(db, lesson_id)
    if not lesson:
        return HTMLResponse("<h4>Không tìm thấy bài học.</h4>", status_code=404)

    progress = None
    related_materials = []

    return templates["student"].TemplateResponse(
        "lesson/lesson_view.html",
        {
            "request": request,
            "lesson": lesson,
            "progress": progress,
            "related_materials": related_materials,
            "active_page": "lesson",
        },
    )


# =====================================================
# ✅ 4️⃣ Đánh dấu bài học hoàn thành
# =====================================================
@router.post("/complete/{lesson_id}", response_class=HTMLResponse, name="student_lesson_mark_complete")
async def mark_lesson_complete(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Học viên đánh dấu bài học đã hoàn thành"""
    try:
        user_id = request.session.get("user_id", "demo-student")
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return HTMLResponse("<h4>Bài học không tồn tại.</h4>", status_code=404)

        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_completed.html",
            {
                "request": request,
                "lesson": lesson,
                "course": getattr(getattr(lesson, "module", None), "course", None),
                "progress": progress,
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [mark_lesson_complete] Exception:", e)
        return HTMLResponse("<h4>Lỗi khi đánh dấu hoàn thành bài học.</h4>", status_code=500)


# =====================================================
# 📝 5️⃣ Ghi chú bài học (GET)
# =====================================================
@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị trang ghi chú của học viên cho một bài học"""
    user_id = request.session.get("user_id", "demo-student")
    lesson = lesson_service.get_lesson_detail(db, lesson_id)
    if not lesson:
        return HTMLResponse("<h4>Không tìm thấy bài học.</h4>", status_code=404)

    notes = lesson_service.get_notes_by_lesson(db, user_id, lesson_id)
    note = notes[0] if notes else None

    return templates["student"].TemplateResponse(
        "lesson/lesson_notes.html",
        {
            "request": request,
            "lesson": lesson,
            "notes": notes,
            "note": note,
            "active_page": "lesson",
        },
    )


# =====================================================
# 💾 6️⃣ Ghi chú bài học (POST)
# =====================================================
@router.post("/notes/{lesson_id}", response_class=HTMLResponse)
async def save_lesson_note(
    request: Request,
    lesson_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    """Lưu ghi chú mới cho bài học"""
    user_id = request.session.get("user_id", "demo-student")
    lesson = lesson_service.get_lesson_detail(db, lesson_id)
    if not lesson:
        return HTMLResponse("<h4>Không tìm thấy bài học.</h4>", status_code=404)

    try:
        lesson_service.add_note_to_lesson(db, user_id, lesson_id, content)
    except Exception as e:
        print("❌ [save_lesson_note] Error:", e)

    return RedirectResponse(
        url=request.url_for("student_lesson_notes", lesson_id=lesson_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
