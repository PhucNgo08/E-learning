"""
==========================================================
🎓 ROUTER: Student - Quiz (FULL 100%)
Hiển thị và xử lý các bài kiểm tra (quiz) của học viên
==========================================================
"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
import traceback

# Cấu hình
from app.config.template_config import templates
from app.database.connection import get_db

# Service
from app.services.student import quiz_service


router = APIRouter(
    prefix="/student/quiz",
    tags=["Student - Quiz"]
)


# ======================================================================
# 🔐 CHECK LOGIN
# ======================================================================
def require_login(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return user_id


# ======================================================================
# 📘 1) Danh sách quiz
# ======================================================================
@router.get("/", response_class=HTMLResponse)
async def quiz_list(request: Request, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        quizzes = quiz_service.get_all_quizzes_for_student(db)

        return templates["student"].TemplateResponse(
            "quiz/quiz_list.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📘 Danh sách bài quiz",
                "active_page": "quiz"
            }
        )

    except Exception as e:
        print("❌ [Quiz][List] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải danh sách quiz.</h4>", 500)


# ======================================================================
# 📗 2) Danh sách quiz theo khóa học
# ======================================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def quiz_by_course(request: Request, course_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        quizzes = quiz_service.get_quizzes_by_course(db, course_id)

        return templates["student"].TemplateResponse(
            "quiz/quiz_list.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📗 Quiz theo khóa học",
                "active_page": "quiz"
            }
        )

    except Exception as e:
        print("❌ [Quiz][ByCourse] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải quiz theo khóa học.</h4>", 500)


# ======================================================================
# 🧩 3) Trang làm bài quiz
# ======================================================================
@router.get("/attempt/{quiz_id}", response_class=HTMLResponse)
async def attempt_quiz(request: Request, quiz_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        quiz = quiz_service.get_quiz_with_questions(db, quiz_id)
        if not quiz:
            return RedirectResponse("/student/quiz", status.HTTP_303_SEE_OTHER)

        # 🔥 Check số lần làm quiz
        attempt_count = quiz_service.get_quiz_attempt_count_for_student(db, user_id, quiz_id)
        if quiz.max_attempts and attempt_count >= quiz.max_attempts:
            return templates["student"].TemplateResponse(
                "quiz/quiz_limit.html",
                {
                    "request": request,
                    "quiz": quiz,
                    "page_title": "🚫 Hết lượt làm bài",
                    "active_page": "quiz"
                }
            )

        return templates["student"].TemplateResponse(
            "quiz/quiz_attempt.html",
            {
                "request": request,
                "quiz": quiz,
                "page_title": f"🧩 Làm bài: {quiz.title}",
                "active_page": "quiz",
            },
        )

    except Exception as e:
        print("❌ [Quiz][Attempt] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi tải bài quiz.</h4>", 500)


# ======================================================================
# 📝 4) Nộp bài quiz
# ======================================================================
@router.post("/submit/{quiz_id}", response_class=HTMLResponse)
async def submit_quiz(request: Request, quiz_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        form = await request.form()
        form_data = dict(form)

        result = quiz_service.submit_quiz(
            db=db, quiz_id=quiz_id, form_data=form_data, user_id=user_id
        )

        if not result or "attempt_id" not in result:
            return HTMLResponse("<h4>❌ Lỗi khi nộp bài quiz.</h4>", 400)

        return RedirectResponse(
            f"/student/quiz/result/{result['attempt_id']}",
            status.HTTP_303_SEE_OTHER,
        )

    except Exception as e:
        print("❌ [Quiz][Submit] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi nộp bài quiz.</h4>", 500)


# ======================================================================
# 🎯 5) Xem kết quả
# ======================================================================
@router.get("/result/{attempt_id}", response_class=HTMLResponse)
async def quiz_result(request: Request, attempt_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        result = quiz_service.get_quiz_result(db, attempt_id)
        if not result:
            return HTMLResponse("<h4>❌ Không tìm thấy kết quả bài quiz.</h4>", 404)

        # ⛔ Không cho xem kết quả của người khác
        if result.user_id != user_id:
            return HTMLResponse("<h4>🚫 Bạn không có quyền xem kết quả này.</h4>", 403)

        return templates["student"].TemplateResponse(
            "quiz/quiz_result.html",
            {
                "request": request,
                "result": result,
                "page_title": "🎯 Kết quả quiz",
                "active_page": "quiz"
            },
        )

    except Exception as e:
        print("❌ [Quiz][Result] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem kết quả.</h4>", 500)


# ======================================================================
# 🕓 6) Lịch sử làm quiz
# ======================================================================
@router.get("/history", response_class=HTMLResponse)
async def quiz_history(request: Request, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

        history = quiz_service.get_quiz_history_for_student(db, user_id)

        return templates["student"].TemplateResponse(
            "quiz/quiz_history.html",
            {
                "request": request,
                "history": history,
                "page_title": "🕓 Lịch sử làm quiz",
                "active_page": "quiz"
            },
        )

    except Exception as e:
        print("❌ [Quiz][History] Lỗi:", e)
        traceback.print_exc()
        return HTMLResponse("<h4>Lỗi khi xem lịch sử.</h4>", 500)


# ======================================================================
# 🚦 Alias redirect
# ======================================================================
@router.get("/../exams", include_in_schema=False)
async def redirect_student_exams():
    return RedirectResponse("/student/quiz")
