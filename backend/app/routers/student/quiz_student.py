from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette import status
from app.services.student import quiz_service

router = APIRouter(prefix="/student/quiz", tags=["Student - Quiz"])
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# =====================================================
# 📘 1. Danh sách quiz (tổng hợp)
# =====================================================
@router.get("/", response_class=HTMLResponse, name="student_quiz_list")
async def quiz_list(request: Request):
    quizzes = quiz_service.get_all_quizzes_for_student()   # ✅ bỏ await
    return templates.TemplateResponse("student/quiz/quiz_list.html", {
        "request": request,
        "quizzes": quizzes
    })

# =====================================================
# 📗 2. Danh sách quiz theo khóa học
# =====================================================
@router.get("/course/{course_id}", response_class=HTMLResponse, name="student_quiz_by_course")
async def quiz_by_course(request: Request, course_id: str):
    quizzes = quiz_service.get_quizzes_by_course(course_id)   # ✅ bỏ await
    return templates.TemplateResponse("student/quiz/quiz_list.html", {
        "request": request,
        "quizzes": quizzes
    })

# =====================================================
# 🧩 3. Làm quiz (attempt)
# =====================================================
@router.get("/attempt/{quiz_id}", response_class=HTMLResponse, name="student_quiz_attempt")
async def attempt_quiz(request: Request, quiz_id: str):
    quiz_data = quiz_service.get_quiz_with_questions(quiz_id)   # ✅ bỏ await
    return templates.TemplateResponse("student/quiz/quiz_attempt.html", {
        "request": request,
        "quiz": quiz_data
    })

# =====================================================
# 📝 4. Nộp bài quiz
# =====================================================
@router.post("/submit/{quiz_id}", response_class=HTMLResponse)
async def submit_quiz(request: Request, quiz_id: str):
    form = await request.form()
    result = quiz_service.submit_quiz(quiz_id, form)   # ✅ bỏ await
    # Sau khi nộp xong → chuyển hướng sang trang kết quả
    return RedirectResponse(
        url=f"/student/quiz/result/{result['attempt_id']}",
        status_code=status.HTTP_303_SEE_OTHER
    )

# =====================================================
# 🎯 5. Xem kết quả
# =====================================================
@router.get("/result/{attempt_id}", response_class=HTMLResponse, name="student_quiz_result")
async def quiz_result(request: Request, attempt_id: str):
    result = quiz_service.get_quiz_result(attempt_id)   # ✅ bỏ await
    return templates.TemplateResponse("student/quiz/quiz_result.html", {
        "request": request,
        "result": result
    })

# =====================================================
# 🕓 6. Lịch sử làm bài
# =====================================================
@router.get("/history", response_class=HTMLResponse, name="student_quiz_history")
async def quiz_history(request: Request):
    history = quiz_service.get_quiz_history_for_student()   # ✅ bỏ await
    return templates.TemplateResponse("student/quiz/quiz_history.html", {
        "request": request,
        "history": history
    })

# =====================================================
# 🚦 ALIAS: /student/exams → redirect về /student/quiz
# =====================================================
from fastapi.responses import RedirectResponse

@router.get("/../exams", include_in_schema=False)
async def redirect_student_exams():
    """Chuyển hướng tất cả request cũ /student/exams về /student/quiz"""
    return RedirectResponse(url="/student/quiz")
