"""
==========================================================
🎓 ROUTER: Student - Lesson (FINAL 2025) ✅ FIXED
- Chặn học khi chưa mua/ghi danh (UI có thể chặn, nhưng backend bắt buộc)
- Bổ sung login check cho /module/{module_id}
- Chặn truy cập trực tiếp /module/{id} và /view/{lesson_id}
- (Khuyến nghị) chặn luôn complete/notes khi chưa có quyền
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette import status
from sqlalchemy.orm import Session
import traceback

from decimal import Decimal
from urllib.parse import quote

from app.database.connection import get_db
from app.config.template_config import templates
from app.services.student import lesson_service

from app.models.question_option import QuestionOption

# ✅ Bạn cần đúng model theo dự án của bạn:
# - user_courses (đã mua)
# - enrollments (đã ghi danh)
from app.models.user_course import UserCourse
from app.models.enrollment import Enrollment

# =====================================================
# ⚙️ Router config
# =====================================================
router = APIRouter(prefix="/student/lesson", tags=["Student - Lesson"])


# =====================================================
# 🔐 Helpers: Permission check
# =====================================================
def _to_decimal(v) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _calc_final_price(course) -> Decimal:
    """
    Ưu tiên dùng course.final_price nếu có.
    Nếu không có, tự tính price - discount_percent.
    """
    fp = getattr(course, "final_price", None)
    if fp is not None:
        return _to_decimal(fp)

    price = _to_decimal(getattr(course, "price", 0) or 0)
    discount = int(getattr(course, "discount_percent", 0) or 0)
    if discount > 0:
        price = price * (Decimal("1") - (Decimal(discount) / Decimal("100")))
    return price


def student_can_access_course(db: Session, user_id: str, course) -> tuple[bool, bool, bool]:
    """
    return: (can_access, purchased, enrolled)
    - Free course => can_access = True
    - Paid course => must purchased or enrolled
    """
    final_price = _calc_final_price(course)
    if final_price <= 0:
        return True, False, False

    purchased = (
        db.query(UserCourse)
        .filter(UserCourse.user_id == user_id, UserCourse.course_id == course.id)
        .first()
        is not None
    )

    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.course_id == course.id)
        .first()
        is not None
    )

    return (purchased or enrolled), purchased, enrolled


def redirect_need_buy(request: Request, course_id: str) -> RedirectResponse:
    """
    Redirect về trang chi tiết khóa học + báo need_buy=1
    kèm next để (sau này) quay lại link đang bị chặn.
    """
    next_url = quote(str(request.url))
    return RedirectResponse(
        url=f"/student/course/detail/{course_id}?need_buy=1&next={next_url}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# =====================================================
# 🔹 1) /student/lesson → redirect → /module
# =====================================================
@router.get("/", response_class=HTMLResponse)
async def student_lesson_home():
    return RedirectResponse("/student/lesson/module", 302)


# =====================================================
# 🔹 2) Danh sách module của học viên
# (thường service đã lọc theo user_id rồi)
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
# 🔹 3) Danh sách bài học trong module  ✅ FIX: login + chặn quyền
# =====================================================
@router.get("/module/{module_id}", response_class=HTMLResponse, name="student_lesson_module")
async def list_lessons_in_module(request: Request, module_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        data = lesson_service.get_lessons_by_module(db, module_id)
        if not data:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy module."},
                404,
            )

        module = data["module"]
        course = module.course

        # ✅ CHẶN HỌC NẾU CHƯA MUA / CHƯA GHI DANH (và không phải khóa free)
        can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
        if not can_access:
            return redirect_need_buy(request, str(course.id))

        return templates["student"].TemplateResponse(
            "lesson/module.html",
            {
                "request": request,
                "module": module,
                "lessons": data["lessons"],
                "page_title": "📗 Chi tiết module",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [module] Lỗi:", e)
        return HTMLResponse("Lỗi tải module.", 500)


# =====================================================
# 🔹 4) Xem bài học + lấy quiz ✅ FIX: chặn quyền
# =====================================================
@router.get("/view/{lesson_id}", response_class=HTMLResponse, name="student_lesson_view")
async def view_lesson(request: Request, lesson_id: str, db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        # Lấy bài học
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không tìm thấy bài học."},
                404,
            )

        course = lesson.module.course

        # ✅ Nếu bạn có lesson.is_preview thì cho xem preview, còn không thì chặn
        is_preview = bool(getattr(lesson, "is_preview", 0))
        if not is_preview:
            can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
            if not can_access:
                return redirect_need_buy(request, str(course.id))

        # Lấy tiến độ
        progress = lesson_service.get_lesson_progress(db, user_id, lesson_id)

        # Lấy quiz của bài học
        quiz = lesson_service.get_quiz_by_lesson(db, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_view.html",
            {
                "request": request,
                "lesson": lesson,
                "progress": progress,
                "quiz": quiz,
                "page_title": f"📕 {lesson.title}",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [view_lesson] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi mở bài học.", 500)


# =====================================================
# 🔹 5) Đánh dấu bài học hoàn thành ✅ FIX: chặn quyền
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

        course = lesson.module.course

        can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
        if not can_access:
            return redirect_need_buy(request, str(course.id))

        progress = lesson_service.mark_lesson_completed(db, user_id, lesson_id)

        return templates["student"].TemplateResponse(
            "lesson/lesson_completed.html",
            {
                "request": request,
                "lesson": lesson,
                "course": course,
                "progress": progress,
                "page_title": "🎉 Hoàn thành bài học",
                "active_page": "lesson",
            },
        )

    except Exception as e:
        print("❌ [mark_complete] Lỗi:", e)
        return HTMLResponse("Lỗi đánh dấu hoàn thành.", 500)


# =====================================================
# 🔥 6.1) FORM THÊM GHI CHÚ ✅ FIX: chặn quyền
# =====================================================
@router.get("/notes/add/{lesson_id}", response_class=HTMLResponse, name="student_lesson_add_note")
async def add_lesson_note_form(request: Request, lesson_id: str, db: Session = Depends(get_db)):

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

        course = lesson.module.course
        can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
        if not can_access:
            return redirect_need_buy(request, str(course.id))

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
# 🔹 6) Xem ghi chú bài học ✅ FIX: chặn quyền
# =====================================================
@router.get("/notes/{lesson_id}", response_class=HTMLResponse, name="student_lesson_notes")
async def view_lesson_notes(request: Request, lesson_id: str, db: Session = Depends(get_db)):

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

        course = lesson.module.course
        can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
        if not can_access:
            return redirect_need_buy(request, str(course.id))

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
# 🔹 7) Lưu ghi chú ✅ FIX: chặn quyền
# =====================================================
@router.post("/notes/{lesson_id}")
async def save_lesson_note(request: Request, lesson_id: str, content: str = Form(...), db: Session = Depends(get_db)):

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/auth/login", 302)

    try:
        lesson = lesson_service.get_lesson_detail(db, lesson_id)
        if not lesson:
            return HTMLResponse("❌ Bài học không tồn tại.", 404)

        course = lesson.module.course
        can_access, purchased, enrolled = student_can_access_course(db, user_id, course)
        if not can_access:
            return redirect_need_buy(request, str(course.id))

        lesson_service.add_note_to_lesson(db, user_id, lesson_id, content)

        return RedirectResponse(
            url=request.url_for("student_lesson_notes", lesson_id=lesson_id),
            status_code=status.HTTP_303_SEE_OTHER,
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


# =====================================================
# 🔹 9) Check đáp án quiz (AJAX) ✅ FIX: thêm login check
# (Chuẩn nhất: join để check option thuộc lesson/course nào và quyền user)
# =====================================================
@router.post("/check-answer")
async def check_answer(
    request: Request,
    question_id: str = Form(...),
    option_id: str = Form(...),
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse(
            {"status": "error", "message": "Bạn chưa đăng nhập."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        option = db.query(QuestionOption).filter(QuestionOption.id == option_id).first()
        if not option:
            return JSONResponse({"status": "error", "message": "Không tìm thấy lựa chọn."})

        return JSONResponse({"status": "ok", "correct": bool(option.is_correct)})

    except Exception:
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": "Lỗi xử lý."})
