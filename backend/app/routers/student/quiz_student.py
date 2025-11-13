"""
==========================================================
🎓 ROUTER: Student - Quiz
Hiển thị và xử lý các bài kiểm tra (quiz) của học viên
==========================================================
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
import traceback

# ✅ Import cấu hình
from app.config.template_config import templates
from app.database.connection import get_db

# ✅ Import service
from app.services.student import quiz_service


# ======================================================
# ⚙️ Cấu hình Router
# ======================================================
router = APIRouter(
    prefix="/student/quiz",
    tags=["Student - Quiz"]
)


# ======================================================
# 📘 1️⃣ Danh sách quiz (tổng hợp)
# ======================================================
@router.get("/", response_class=HTMLResponse, name="student_quiz_list")
async def quiz_list(request: Request, db=Depends(get_db)):
    """Hiển thị danh sách tất cả quiz mà sinh viên có thể làm."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        quizzes = quiz_service.get_all_quizzes_for_student(db)
        return templates["student"].TemplateResponse(
            "quiz/quiz_list.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📘 Danh sách bài quiz",
                "active_page": "quiz",
            },
        )
    except Exception as e:
        print("❌ [Quiz][ListAll] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách quiz.</h4>", status_code=500)


# ======================================================
# 📗 2️⃣ Danh sách quiz theo khóa học
# ======================================================
@router.get("/course/{course_id}", response_class=HTMLResponse, name="student_quiz_by_course")
async def quiz_by_course(request: Request, course_id: str, db=Depends(get_db)):
    """Hiển thị danh sách quiz thuộc một khóa học cụ thể."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        quizzes = quiz_service.get_quizzes_by_course(db, course_id)
        return templates["student"].TemplateResponse(
            "quiz/quiz_list.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📗 Quiz theo khóa học",
                "active_page": "quiz",
            },
        )
    except Exception as e:
        print("❌ [Quiz][ListByCourse] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách quiz theo khóa học.</h4>", status_code=500)


# ======================================================
# 🧩 3️⃣ Làm quiz (attempt)
# ======================================================
@router.get("/attempt/{quiz_id}", response_class=HTMLResponse, name="student_quiz_attempt")
async def attempt_quiz(request: Request, quiz_id: str, db=Depends(get_db)):
    """Trang làm bài quiz."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        quiz_data = quiz_service.get_quiz_with_questions(db, quiz_id)
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
    except Exception as e:
        print("❌ [Quiz][Attempt] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải bài quiz.</h4>", status_code=500)


# ======================================================
# 📝 4️⃣ Nộp bài quiz
# ======================================================
@router.post("/submit/{quiz_id}", response_class=HTMLResponse)
async def submit_quiz(request: Request, quiz_id: str, db=Depends(get_db)):
    """Xử lý sinh viên nộp bài quiz."""
    try:
        form = await request.form()
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        result = quiz_service.submit_quiz(db=db, quiz_id=quiz_id, form_data=form, user_id=user_id)
        if not result:
            return HTMLResponse("<h4>❌ Lỗi khi nộp bài quiz.</h4>", status_code=400)

        print(f"✅ [Quiz][Submit] user={user_id}, quiz={quiz_id}, score={result.get('score')}")
        return RedirectResponse(
            url=f"/student/quiz/result/{result['attempt_id']}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        print("❌ [Quiz][Submit] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xử lý nộp bài quiz.</h4>", status_code=500)


# ======================================================
# 🎯 5️⃣ Xem kết quả quiz
# ======================================================
@router.get("/result/{attempt_id}", response_class=HTMLResponse, name="student_quiz_result")
async def quiz_result(request: Request, attempt_id: str, db=Depends(get_db)):
    """Hiển thị kết quả làm quiz."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        result = quiz_service.get_quiz_result(db, attempt_id)
        if not result:
            return HTMLResponse("<h4>❌ Không tìm thấy kết quả quiz.</h4>", status_code=404)

        return templates["student"].TemplateResponse(
            "quiz/quiz_result.html",
            {
                "request": request,
                "result": result,
                "page_title": "🎯 Kết quả bài quiz",
                "active_page": "quiz",
            },
        )
    except Exception as e:
        print("❌ [Quiz][Result] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem kết quả quiz.</h4>", status_code=500)


# ======================================================
# 🕓 6️⃣ Lịch sử làm quiz
# ======================================================
@router.get("/history", response_class=HTMLResponse, name="student_quiz_history")
async def quiz_history(request: Request, db=Depends(get_db)):
    """Hiển thị lịch sử các lần làm quiz."""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)

        history = quiz_service.get_quiz_history_for_student(db, user_id)
        return templates["student"].TemplateResponse(
            "quiz/quiz_history.html",
            {
                "request": request,
                "history": history,
                "page_title": "🕓 Lịch sử làm quiz",
                "active_page": "quiz",
            },
        )
    except Exception as e:
        print("❌ [Quiz][History] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải lịch sử quiz.</h4>", status_code=500)


# ======================================================
# 🚦 ALIAS: /student/exams → redirect về /student/quiz
# ======================================================
@router.get("/../exams", include_in_schema=False)
async def redirect_student_exams():
    """Chuyển hướng request cũ /student/exams về /student/quiz."""
    return RedirectResponse(url="/student/quiz")
