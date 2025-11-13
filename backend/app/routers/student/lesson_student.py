"""
==========================================================
🎓 ROUTER: Student - Lesson
Xử lý các chức năng xem bài học và module của học viên
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from sqlalchemy.orm import Session
import traceback

# ✅ Import cấu hình DB & template
from app.database.connection import get_db
from app.config.template_config import templates

# ✅ Import service & models
from app.services.student import lesson_service


# =====================================================
# ⚙️ Cấu hình Router
# =====================================================
router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])


# =====================================================
# 🏠 0️⃣ Trang mặc định /student/lesson
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def student_lesson_home():
    """Chuyển hướng sang danh sách module."""
    return RedirectResponse(url="/student/lesson/module", status_code=status.HTTP_302_FOUND)


# =====================================================
# 📘 1️⃣ Danh sách tất cả module mà sinh viên đang học
# =====================================================
@router.get("/module", response_class=HTMLResponse, name="student_lesson_module_list")
async def list_all_modules(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tất cả module mà học viên đã ghi danh."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        modules = lesson_service.get_modules_for_student(db, user_id)
        if not modules:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Bạn chưa tham gia khóa học hoặc chưa có module nào."},
                status_code=404,
            )

        return templates["student"].TemplateResponse(
            "lesson/module_list.html",
            {
                "request": request,
                "modules": modules,
                "page_title": "📘 Danh sách module của bạn",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [list_all_modules] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách module.</h4>", status_code=500)


# =====================================================
# 📗 2️⃣ Danh sách bài học trong 1 module
# =====================================================
@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):
    """Hiển thị danh sách bài học thuộc 1 module."""
    try:
        data = lesson_service.get_lessons_by_module(db, module_id)
        if not data:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy module hoặc bài học."},
                status_code=404,
            )

        module = data["module"]
        lessons = data["lessons"]

        return templates["student"].TemplateResponse(
            "lesson/module.html",
            {
                "request": request,
                "module": module,
                "lessons": lessons,
                "page_title": f"📗 {module.title}",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [list_lessons_in_module] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải bài học.</h4>", status_code=500)


# =====================================================
# 📕 3️⃣ Xem chi tiết 1 bài học
# =====================================================
@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị chi tiết nội dung của 1 bài học."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài học."},
                status_code=404,
            )

        progress = lesson_service.get_lesson_progress(db, user_id, lesson_id)
        related_materials = []  # 🔸 Có thể tích hợp course_material_service sau

        return templates["student"].TemplateResponse(
            "lesson/lesson_view.html",
            {
                "request": request,
                "lesson": lesson,
                "progress": progress,
                "related_materials": related_materials,
                "page_title": f"📕 {lesson.title}",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [view_lesson] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi hiển thị bài học.</h4>", status_code=500)


# =====================================================
# ✅ 4️⃣ Đánh dấu bài học hoàn thành
# =====================================================
@router.post("/complete/{lesson_id}", response_class=HTMLResponse, name="student_lesson_mark_complete")
async def mark_lesson_complete(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Học viên đánh dấu bài học đã hoàn thành."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Bài học không tồn tại."},
                status_code=404,
            )

        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)
        print(f"✅ [Lesson Complete] User={user_id}, Lesson={lesson_id}")

        return templates["student"].TemplateResponse(
            "lesson/lesson_completed.html",
            {
                "request": request,
                "lesson": lesson,
                "course": getattr(getattr(lesson, "module", None), "course", None),
                "progress": progress,
                "page_title": "🎉 Hoàn thành bài học",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        db.rollback()
        print("❌ [mark_lesson_complete] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi đánh dấu hoàn thành bài học.</h4>", status_code=500)


# =====================================================
# 📝 5️⃣ Xem ghi chú bài học
# =====================================================
@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    """Hiển thị trang ghi chú của học viên cho một bài học."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html", {"request": request, "message": "❌ Không tìm thấy bài học."}, status_code=404
            )

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
        print("❌ [view_lesson_notes] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải ghi chú.</h4>", status_code=500)


# =====================================================
# 💾 6️⃣ Lưu ghi chú bài học
# =====================================================
@router.post("/notes/{lesson_id}")
async def save_lesson_note(
    request: Request,
    lesson_id: str,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    """Lưu ghi chú mới cho bài học."""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html", {"request": request, "message": "❌ Không tìm thấy bài học."}, status_code=404
            )

        lesson_service.add_note_to_lesson(db, user_id, lesson_id, content)
        print(f"💾 [Lesson Note] User={user_id} ➜ Lesson={lesson_id}")

        return RedirectResponse(
            url=request.url_for("student_lesson_notes", lesson_id=lesson_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        db.rollback()
        print("❌ [save_lesson_note] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi lưu ghi chú.</h4>", status_code=500)
# =====================================================
# 📊 7️⃣ Theo dõi tiến độ học tập
# =====================================================
@router.get("/progress", response_class=HTMLResponse, name="student_lesson_progress")
async def view_learning_progress(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị tiến độ học tập của học viên trên tất cả khóa học.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

    try:
        progress_data = lesson_service.get_learning_progress(db, user_id)

        if not progress_data:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Bạn chưa có tiến độ học tập nào."},
                status_code=404,
            )

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
        print("❌ [view_learning_progress] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải tiến độ học tập.</h4>", status_code=500)
