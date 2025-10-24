"""
==========================================================
🎓 ROUTER: Student - Lesson
Xử lý các chức năng xem bài học và module của học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette import status
from app.database.connection import get_db
from app.services.student import lesson_service
from app.models.lesson_note import LessonNote   # ✅ đúng tên model
from datetime import datetime
import uuid

# =====================================================
# ⚙️ Cấu hình Router
# =====================================================
router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# =====================================================
# 📘 1️⃣ Danh sách bài học trong 1 module
# =====================================================
@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):
    """Hiển thị danh sách bài học thuộc 1 module"""
    data = lesson_service.get_lessons_by_module(db, module_id)
    if not data:
        return HTMLResponse("<h4>Không tìm thấy module hoặc bài học.</h4>", status_code=404)

    module = data["module"]
    lessons = data["lessons"]

    return templates.TemplateResponse(
        "student/lesson/module.html",
        {
            "request": request,
            "module": module,
            "lessons": lessons,
            "active_page": "lessons",
        },
    )


# =====================================================
# 📗 2️⃣ Xem chi tiết 1 bài học
# =====================================================
@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị chi tiết nội dung của 1 bài học"""
    lesson = lesson_service.get_lesson_detail(db, lesson_id)
    if not lesson:
        return HTMLResponse("<h4>Không tìm thấy bài học.</h4>", status_code=404)

    progress = None
    related_materials = []

    return templates.TemplateResponse(
        "student/lesson/lesson_view.html",
        {
            "request": request,
            "lesson": lesson,
            "progress": progress,
            "related_materials": related_materials,
            "active_page": "lessons",
        },
    )


# =====================================================
# ✅ 3️⃣ Đánh dấu bài học hoàn thành
# =====================================================
@router.post("/complete/{lesson_id}", response_class=HTMLResponse, name="student_lesson_mark_complete")
async def mark_lesson_complete(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Học viên đánh dấu bài học đã hoàn thành"""
    try:
        user_id = request.session.get("user_id", "demo-student")
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return HTMLResponse("<h4>Bài học không tồn tại.</h4>", status_code=404)

        # ✅ Gọi service cập nhật tiến độ
        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)

        # 🔁 Hiển thị trang hoàn thành (đúng file)
        return templates.TemplateResponse(
            "student/lesson/lesson_completed.html",   # ✅ đúng tên file
            {
                "request": request,
                "lesson": lesson,
                "course": getattr(getattr(lesson, "module", None), "course", None),
                "progress": progress,
                "active_page": "lessons",
            },
        )

    except Exception as e:
        print("❌ [mark_lesson_complete] Exception:", e)
        return HTMLResponse("<h4>Lỗi khi đánh dấu hoàn thành bài học.</h4>", status_code=500)


# =====================================================
# 📝 4️⃣ Ghi chú bài học (GET + POST)
# =====================================================
@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị trang ghi chú của học viên cho một bài học"""
    user_id = request.session.get("user_id", "demo-student")
    lesson = lesson_service.get_lesson_detail(db, lesson_id)
    if not lesson:
        return HTMLResponse("<h4>Không tìm thấy bài học.</h4>", status_code=404)

    notes = (
        db.query(LessonNote)
        .filter(LessonNote.user_id == user_id, LessonNote.lesson_id == lesson_id)
        .order_by(LessonNote.created_at.desc())
        .all()
    )
    note = notes[0] if notes else None

    return templates.TemplateResponse(
        "student/lesson/lesson_notes.html",
        {
            "request": request,
            "lesson": lesson,
            "notes": notes,
            "note": note,
            "active_page": "lessons",
        },
    )


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
        new_note = LessonNote(
            id=str(uuid.uuid4()),
            user_id=user_id,
            lesson_id=lesson_id,
            content=content,
            created_at=datetime.utcnow(),
        )
        db.add(new_note)
        db.commit()

    except Exception as e:
        print("❌ [save_lesson_note] Error:", e)

    return RedirectResponse(
        url=request.url_for("student_lesson_notes", lesson_id=lesson_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
