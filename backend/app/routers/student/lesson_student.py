"""
==========================================================
🎓 ROUTER: Student - Lesson (FINAL 2025)
Xử lý module, lesson, progress và ghi chú học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from sqlalchemy.orm import Session
import traceback

from app.database.connection import get_db
from app.config.template_config import templates

from app.services.student import lesson_service


# =====================================================
# ⚙️ Router config
# =====================================================
router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])


# =====================================================
# 🔹 1) /student/lesson → redirect → /module
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def student_lesson_home():
    return RedirectResponse("/student/lesson/module", 302)


# =====================================================
# 🔹 2) Danh sách module của học viên
# =====================================================
@router.get("/module", response_class=HTMLResponse, name="student_lesson_module_list")
async def list_all_modules(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        modules = lesson_service.get_modules_for_student(db, user_id)

        return templates["student"].TemplateResponse(
            "lesson/module_list.html",
            {
                "request": request,
                "modules": modules,
                "page_title": "📘 Danh sách module",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [module_list] Lỗi:", e)
        return HTMLResponse("Lỗi tải danh sách module.", 500)


# =====================================================
# 🔹 3) Danh sách bài học trong module
# =====================================================
@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):

    try:
        data = lesson_service.get_lessons_by_module(db, module_id)
        if not data:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy module."},
                404,
            )

        return templates["student"].TemplateResponse(
            "lesson/module.html",
            {
                "request": request,
                "module": data["module"],
                "lessons": data["lessons"],
                "page_title": "📗 Chi tiết module",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [module] Lỗi:", e)
        return HTMLResponse("Lỗi tải module.", 500)


# =====================================================
# 🔹 4) Xem bài học
# =====================================================
@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)

        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài học."},
                404,
            )

        progress = lesson_service.get_lesson_progress(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_view.html",
            {
                "request": request,
                "lesson": lesson,
                "progress": progress,
                "page_title": f"📕 {lesson.title}",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [view_lesson] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi mở bài học.", 500)


# =====================================================
# 🔹 5) Đánh dấu bài học hoàn thành
# =====================================================
@router.post("/complete/{lesson_id}", name="student_lesson_mark_complete")
async def mark_lesson_complete(request: Request, lesson_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return HTMLResponse("❌ Bài học không tồn tại.", 404)

        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_completed.html",
            {
                "request": request,
                "lesson": lesson,
                "course": lesson.module.course,
                "progress": progress,
                "page_title": "🎉 Hoàn thành bài học",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [mark_complete] Lỗi:", e)
        return HTMLResponse("Lỗi đánh dấu hoàn thành.", 500)


# =====================================================
# 🔥 6.1) FORM THÊM GHI CHÚ
# ⚠ ĐẶT LÊN TRÊN /notes/{lesson_id} để KHÔNG BỊ NUỐT ROUTE
# =====================================================
@router.get("/notes/add/{lesson_id}", response_class=HTMLResponse, name="student_lesson_add_note")
async def add_lesson_note_form(request: Request, lesson_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/note_form.html",
            {
                "request": request,
                "lesson": lesson,
                "page_title": "🖋️ Thêm ghi chú",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [note_form] Lỗi:", e)
        return HTMLResponse("Lỗi mở form thêm ghi chú.", 500)


# =====================================================
# 🔹 6) Xem ghi chú bài học
# =====================================================
@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        notes = lesson_service.get_notes_by_lesson(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_notes.html",
            {
                "request": request,
                "lesson": lesson,
                "notes": notes,
                "page_title": "📝 Ghi chú bài học",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [lesson_notes] Lỗi:", e)
        return HTMLResponse("Lỗi tải ghi chú.", 500)


# =====================================================
# 🔹 7) Lưu ghi chú
# =====================================================
@router.post("/notes/{lesson_id}")
async def save_lesson_note(request: Request, lesson_id: str, content: str = Form(...), db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson_service.add_note_to_lesson(db, user_id, lesson_id, content)

        return RedirectResponse(
            url=request.url_for("student_lesson_notes", lesson_id=lesson_id),
            status_code=303,
        )

    except Exception as e:
        print("❌ [save_note] Lỗi:", e)
        return HTMLResponse("Lỗi khi lưu ghi chú.", 500)


# =====================================================
# 🔹 8) Tiến độ học tập tổng thể
# =====================================================
@router.get("/progress", response_class=HTMLResponse, name="student_lesson_progress")
async def view_learning_progress(request: Request, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        progress_data = lesson_service.get_learning_progress(db, user_id)

        return templates["student"].TemplateResponse(
            "lesson/progress.html",
            {
                "request": request,
                "progress_data": progress_data,
                "page_title": "📊 Tiến độ học tập",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [progress] Lỗi:", e)
        return HTMLResponse("Lỗi khi tải tiến độ.", 500)
