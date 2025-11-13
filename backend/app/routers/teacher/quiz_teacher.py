"""
==========================================================
🎓 ROUTER: Teacher - Quiz Management
Quản lý tạo, sửa, xóa, xem chi tiết và thống kê Quiz của giáo viên
==========================================================
"""

from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# ✅ Import nội bộ
from app.database.connection import get_db
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

# ✅ Import services & models
from app.services.teacher import quiz_service
from app.models.course import Course
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz import Quiz


# ======================================================
# ⚙️ Router
# ======================================================
router = APIRouter(
    prefix="/teacher/quizzes",
    tags=["Teacher - Quizzes"]
)


# ======================================================
# 🧭 0️⃣ Redirect gốc → /list
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root():
    """Chuyển /teacher/quizzes → /teacher/quizzes/list"""
    return RedirectResponse("/teacher/quizzes/list", status_code=303)


# ======================================================
# 📋 1️⃣ Danh sách quiz của giáo viên
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def list_quizzes(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách quiz mà giáo viên đã tạo"""
    teacher = current_teacher
    quizzes = quiz_service.get_quizzes_by_teacher(db, teacher.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "quizzes/list.html",
        {
            "request": request,
            "teacher": teacher,
            "quizzes": quizzes,
            "page_title": "📘 Danh sách Quiz của bạn",
            "now": datetime.now(),
        },
    )


# ======================================================
# ➕ 2️⃣ Tạo quiz (GET)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_quiz_page(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form tạo quiz"""
    teacher = current_teacher
    courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "quizzes/create.html",
        {
            "request": request,
            "teacher": teacher,
            "courses": courses,
            "page_title": "➕ Tạo Quiz mới",
        },
    )


# ======================================================
# 💾 3️⃣ Xử lý tạo quiz (POST)
# ======================================================
@router.post("/create")
def create_quiz(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    quiz_type: str = Form("practice"),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(None),
    total_questions: int = Form(10),
    passing_score: float = Form(60.0),
    max_attempts: int = Form(1)
):
    """Tạo mới một quiz"""
    teacher_id = current_teacher.id
    course = db.query(Course).filter(Course.id == course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học hoặc không có quyền.")

    quiz_service.create_quiz(
        db,
        teacher_id,
        course_id,
        title,
        description,
        quiz_type,
        difficulty_level,
        time_limit_minutes,
        max_attempts,
        passing_score,
        total_questions
    )

    return RedirectResponse("/teacher/quizzes/list", status_code=303)


# ======================================================
# ✏️ 4️⃣ Sửa quiz (GET)
# ======================================================
@router.get("/edit/{quiz_id}", response_class=HTMLResponse)
def edit_quiz_page(
    quiz_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form chỉnh sửa quiz"""
    quiz = quiz_service.get_quiz_by_id(db, quiz_id, current_teacher.id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz hoặc không có quyền.")

    courses = db.query(Course).filter(Course.teacher_id == current_teacher.id).all()

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "quizzes/edit.html",
        {
            "request": request,
            "teacher": current_teacher,
            "quiz": quiz,
            "courses": courses,
            "page_title": f"✏️ Chỉnh sửa Quiz: {quiz.title}",
        },
    )


# ======================================================
# 💾 5️⃣ Cập nhật quiz (POST)
# ======================================================
@router.post("/edit/{quiz_id}")
def edit_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    quiz_type: str = Form("practice"),
    difficulty_level: str = Form("medium"),
    time_limit_minutes: int = Form(None),
    total_questions: int = Form(10),
    passing_score: float = Form(60.0),
    max_attempts: int = Form(1)
):
    """Cập nhật quiz"""
    updated = quiz_service.update_quiz(
        db,
        current_teacher.id,
        quiz_id,
        course_id,
        title,
        description,
        quiz_type,
        difficulty_level,
        time_limit_minutes,
        max_attempts,
        passing_score,
        total_questions
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz hoặc không có quyền.")

    return RedirectResponse("/teacher/quizzes/list", status_code=303)


# ======================================================
# 🗑️ 6️⃣ Xóa quiz
# ======================================================
@router.post("/delete/{quiz_id}")
def delete_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xóa quiz"""
    deleted = quiz_service.delete_quiz(db, current_teacher.id, quiz_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz hoặc không có quyền xóa.")

    return RedirectResponse("/teacher/quizzes/list", status_code=303)


# ======================================================
# 📊 7️⃣ Xem chi tiết quiz
# ======================================================
@router.get("/detail/{quiz_id}", response_class=HTMLResponse)
def quiz_detail(
    quiz_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xem chi tiết quiz và câu hỏi"""
    quiz = quiz_service.get_quiz_detail(db, current_teacher.id, quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz hoặc không có quyền truy cập.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "quizzes/detail.html",
        {
            "request": request,
            "teacher": current_teacher,
            "quiz": quiz,
            "questions": quiz.questions,
            "page_title": f"📊 Chi tiết Quiz: {quiz.title}",
        },
    )


# ======================================================
# 📈 8️⃣ Thống kê kết quả học viên
# ======================================================
@router.get("/statistics/{quiz_id}", response_class=HTMLResponse)
def quiz_statistics(
    quiz_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Thống kê kết quả học viên cho quiz"""
    data = quiz_service.get_quiz_statistics(db, current_teacher.id, quiz_id)
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy quiz hoặc không có quyền truy cập.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "quizzes/statistics.html",
        {
            "request": request,
            "teacher": current_teacher,
            "quiz": data["quiz"],
            "stats": data["stats"],
            "top_students": data["top_students"],
            "page_title": f"📈 Thống kê kết quả: {data['quiz'].title}",
        },
    )


# ======================================================
# 📊 9️⃣ API phụ trợ cho Chart.js (phân bố điểm & tỉ lệ đạt)
# ======================================================
@router.get("/api/score-distribution/{quiz_id}")
def api_score_distribution(
    quiz_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """API trả về phân bố điểm cho biểu đồ Chart.js"""
    quiz = (
        db.query(Quiz)
        .join(Course, Quiz.course_id == Course.id)
        .filter(Course.teacher_id == current_teacher.id, Quiz.id == quiz_id)
        .first()
    )
    if not quiz:
        raise HTTPException(status_code=404, detail="Không có quyền truy cập quiz này.")

    ranges = [(0, 50), (50, 70), (70, 90), (90, 100)]
    counts = []
    for low, high in ranges:
        count = (
            db.query(func.count(QuizAttempt.id))
            .filter(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.status == "submitted",
                QuizAttempt.score >= low,
                QuizAttempt.score < high
            )
            .scalar()
        )
        counts.append(count or 0)

    total = sum(counts)
    passed = sum(count for (low, high), count in zip(ranges, counts) if high >= quiz.passing_score)
    failed = total - passed
    return {"counts": counts, "passed": passed, "failed": failed}
