"""
==========================================================
🎓 ROUTER: Student - Quiz
Hiển thị và xử lý các bài kiểm tra (quiz) của học viên
==========================================================
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status

# ✅ Import cấu hình template động
from app.config.template_config import templates

# ✅ Import service
from app.services.student import quiz_service


# =====================================================
# ⚙️ Cấu hình Router
# =====================================================
router = APIRouter(prefix="/student/quiz", tags=["Student - Quiz"])


# =====================================================
# 📘 1. Danh sách quiz (tổng hợp)
# =====================================================
@router.get("/", response_class=HTMLResponse, name="student_quiz_list")
async def quiz_list(request: Request):
    """Hiển thị danh sách tất cả quiz mà sinh viên có thể làm"""
    quizzes = quiz_service.get_all_quizzes_for_student()
    return templates["student"].TemplateResponse(
        "quiz/quiz_list.html",
        {
            "request": request,
            "quizzes": quizzes,
            "page_title": "📘 Danh sách bài quiz",
            "active_page": "quiz",
        },
    )


# =====================================================
# 📗 2. Danh sách quiz theo khóa học
# =====================================================
@router.get("/course/{course_id}", response_class=HTMLResponse, name="student_quiz_by_course")
async def quiz_by_course(request: Request, course_id: str):
    """Hiển thị danh sách quiz thuộc 1 khóa học cụ thể"""
    quizzes = quiz_service.get_quizzes_by_course(course_id)
    return templates["student"].TemplateResponse(
        "quiz/quiz_list.html",
        {
            "request": request,
            "quizzes": quizzes,
            "page_title": "📗 Quiz theo khóa học",
            "active_page": "quiz",
        },
    )


# =====================================================
# 🧩 3. Làm quiz (attempt)
# =====================================================
@router.get("/attempt/{quiz_id}", response_class=HTMLResponse, name="student_quiz_attempt")
async def attempt_quiz(request: Request, quiz_id: str):
    """Trang làm bài quiz"""
    quiz_data = quiz_service.get_quiz_with_questions(quiz_id)
    if not quiz_data:
        return RedirectResponse(url="/student/quiz", status_code=status.HTTP_303_SEE_OTHER)

    return templates["student"].TemplateResponse(
        "quiz/quiz_attempt.html",
        {
            "request": request,
            "quiz": quiz_data,
            "page_title": "🧩 Làm bài quiz",
            "active_page": "quiz",
        },
    )


# =====================================================
# 📝 4. Nộp bài quiz
# =====================================================
@router.post("/submit/{quiz_id}", response_class=HTMLResponse)
async def submit_quiz(request: Request, quiz_id: str):
    """Xử lý sinh viên nộp bài quiz"""
    form = await request.form()
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    result = quiz_service.submit_quiz(quiz_id=quiz_id, form_data=form, user_id=user_id)
    if not result:
        return HTMLResponse("❌ Lỗi khi nộp bài quiz.", status_code=400)

    return RedirectResponse(
        url=f"/student/quiz/result/{result['attempt_id']}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# =====================================================
# 🎯 5. Xem kết quả quiz
# =====================================================
@router.get("/result/{attempt_id}", response_class=HTMLResponse, name="student_quiz_result")
async def quiz_result(request: Request, attempt_id: str):
    """Hiển thị kết quả làm quiz"""
    result = quiz_service.get_quiz_result(attempt_id)
    if not result:
        return HTMLResponse("❌ Không tìm thấy kết quả.", status_code=404)

    return templates["student"].TemplateResponse(
        "quiz/quiz_result.html",
        {
            "request": request,
            "result": result,
            "page_title": "🎯 Kết quả bài quiz",
            "active_page": "quiz",
        },
    )


# =====================================================
# 🕓 6. Lịch sử làm bài quiz
# =====================================================
@router.get("/history", response_class=HTMLResponse, name="student_quiz_history")
async def quiz_history(request: Request):
    """Hiển thị lịch sử các lần làm quiz"""
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    history = quiz_service.get_quiz_history_for_student(user_id)
    return templates["student"].TemplateResponse(
        "quiz/quiz_history.html",
        {
            "request": request,
            "history": history,
            "page_title": "🕓 Lịch sử làm quiz",
            "active_page": "quiz",
        },
    )


# =====================================================
# 🚦 ALIAS: /student/exams → redirect về /student/quiz
# =====================================================
@router.get("/../exams", include_in_schema=False)
async def redirect_student_exams():
    """Chuyển hướng request cũ /student/exams về /student/quiz"""
    return RedirectResponse(url="/student/quiz")
