"""
==========================================================
🎓 ROUTER: Student - Quiz (Practice + Graded Exam)
FINAL PRO MAX 2025 – Synced with Quiz Service v12
==========================================================
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette import status
from sqlalchemy.orm import joinedload
from datetime import datetime
import random
import traceback

from app.config.template_config import templates
from app.database.connection import get_db

# ==========================================================
# Import Service từ quiz_service_full_v12
# ==========================================================
from app.services.quiz_service_full_v12 import (
    get_all_quizzes_for_student_enrolled,
    get_quizzes_by_course,
    submit_quiz,
    get_quiz_result,
    get_quiz_history_for_student,
    get_quiz_attempt_count_for_student,
)

from app.models.quiz import Quiz
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.enrollment import Enrollment


# ==========================================================
# Router Init
# ==========================================================
router = APIRouter(
    prefix="/student/quiz",
    tags=["Student - Quiz"],
)


# ==========================================================
# Helper: Check Login
# ==========================================================
def require_login(request: Request):
    return request.session.get("user_id")


# ==========================================================
# 1) Danh sách quiz (Practice + Graded)
# ==========================================================
@router.get("/", response_class=HTMLResponse)
async def quiz_list(request: Request, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        quizzes = get_all_quizzes_for_student_enrolled(db, user_id)

        return templates["student"].TemplateResponse(
            "quiz/quiz_list.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📘 Danh sách bài Quiz",
                "active_page": "quiz",
                "datetime": datetime,        # ⭐ Quan trọng: dùng trong template
                "now": datetime.utcnow(),
            }
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải danh sách quiz.", 500)


# ==========================================================
# 2) Quiz theo khóa học
# ==========================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def quiz_by_course(request: Request, course_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        quizzes = get_quizzes_by_course(db, course_id)

        return templates["student"].TemplateResponse(
            "quiz/quiz_list_by_course.html",
            {
                "request": request,
                "quizzes": quizzes,
                "page_title": "📘 Quiz theo khóa học",
                "active_page": "quiz",
                "datetime": datetime,
                "now": datetime.utcnow(),
            }
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải quiz theo khóa học.", 500)


# ==========================================================
# 3) Attempt Quiz (Practice + Graded)
# ==========================================================
@router.get("/attempt/{quiz_id}", response_class=HTMLResponse)
async def attempt_quiz(request: Request, quiz_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        quiz = (
            db.query(Quiz)
            .options(joinedload(Quiz.questions).joinedload(Question.options))
            .filter(Quiz.id == quiz_id)
            .first()
        )

        if not quiz:
            return HTMLResponse("Quiz không tồn tại.", 404)

        # =====================================================
        # PRACTICE → random câu hỏi + đáp án
        # =====================================================
        if quiz.quiz_type == "practice":
            if quiz.randomize_questions:
                quiz.questions = list(quiz.questions)
                random.shuffle(quiz.questions)

            if quiz.randomize_options:
                for q in quiz.questions:
                    q.options = list(q.options)
                    random.shuffle(q.options)

        # =====================================================
        # GRADED → kiểm tra nghiêm ngặt
        # =====================================================
        if quiz.quiz_type == "graded":

            # 1) Quiz phải approved + published
            if not quiz.is_approved or quiz.status != "published":
                return HTMLResponse("🚫 Bài thi chưa được mở.", 403)

            # 2) Học viên phải ghi danh khóa học
            enrollment = (
                db.query(Enrollment)
                .filter(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == quiz.course_id,
                    Enrollment.enrollment_status.in_(
                        ["active", "approved", "completed"]
                    ),
                )
                .first()
            )
            if not enrollment:
                return HTMLResponse("🚫 Bạn không học khóa này.", 403)

            # 3) Kiểm tra thời gian mở – đóng
            now = datetime.utcnow()

            if quiz.available_from and now < quiz.available_from:
                return HTMLResponse("🚫 Bài thi chưa mở.", 403)

            if quiz.available_to and now > quiz.available_to:
                return HTMLResponse("🚫 Bài thi đã kết thúc.", 403)

            # 4) Kiểm tra số lượt làm
            attempts = get_quiz_attempt_count_for_student(db, user_id, quiz_id)
            if quiz.max_attempts and attempts >= quiz.max_attempts:
                return templates["student"].TemplateResponse(
                    "quiz/quiz_limit.html",
                    {"request": request, "quiz": quiz},
                )

        # =====================================================
        # OK → cho phép làm bài
        # =====================================================
        request.session["quiz_started_at"] = datetime.utcnow().isoformat()

        return templates["student"].TemplateResponse(
            "quiz/quiz_attempt.html",
            {
                "request": request,
                "quiz": quiz,
                "page_title": f"🧩 Làm bài: {quiz.title}",
                "active_page": "quiz",
            }
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi khi tải bài quiz.", 500)


# ==========================================================
# 4) Submit quiz
# ==========================================================
@router.post("/submit/{quiz_id}", response_class=HTMLResponse)
async def submit_quiz_post(request: Request, quiz_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        form = await request.form()
        form_data = dict(form)

        # Add started_at từ session
        if "quiz_started_at" in request.session:
            form_data["started_at"] = request.session["quiz_started_at"]

        # chống double-submit
        if request.session.get("submitted_flag"):
            return HTMLResponse("⏳ Đang xử lý, vui lòng đợi…", 400)

        request.session["submitted_flag"] = True

        # Gọi service
        result = submit_quiz(db, quiz_id, form_data, user_id)

        # clear flag
        request.session.pop("submitted_flag", None)

        if not result or "attempt_id" not in result:
            return HTMLResponse("❌ Lỗi khi nộp bài quiz.", 400)

        return RedirectResponse(
            f"/student/quiz/result/{result['attempt_id']}",
            status_code=303,
        )

    except Exception:
        request.session.pop("submitted_flag", None)
        traceback.print_exc()
        return HTMLResponse("Lỗi khi nộp bài quiz.", 500)


# ==========================================================
# 5) Xem kết quả
# ==========================================================
@router.get("/result/{attempt_id}", response_class=HTMLResponse)
async def quiz_result_page(request: Request, attempt_id: str, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        result = get_quiz_result(db, attempt_id)
        if not result:
            return HTMLResponse("Không tìm thấy kết quả.", 404)

        if result.user_id != user_id:
            return HTMLResponse("🚫 Bạn không có quyền xem bài này.", 403)

        return templates["student"].TemplateResponse(
            "quiz/quiz_result.html",
            {
                "request": request,
                "result": result,
                "page_title": "🎯 Kết quả bài làm",
                "active_page": "quiz",
            }
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi khi xem kết quả.", 500)


# ==========================================================
# 6) Lịch sử quiz
# ==========================================================
@router.get("/history", response_class=HTMLResponse)
async def quiz_history(request: Request, db=Depends(get_db)):
    try:
        user_id = require_login(request)
        if not user_id:
            return RedirectResponse("/auth/login", 302)

        history = get_quiz_history_for_student(db, user_id)

        return templates["student"].TemplateResponse(
            "quiz/quiz_history.html",
            {
                "request": request,
                "history": history,
                "page_title": "🕓 Lịch sử làm bài",
                "active_page": "quiz",
            }
        )

    except Exception:
        traceback.print_exc()
        return HTMLResponse("Lỗi khi xem lịch sử.", 500)
