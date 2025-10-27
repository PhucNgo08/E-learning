from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz_attempt import QuizAttempt
from app.models.course_review import CourseReview
from app.models.lesson_progress import LessonProgress
from datetime import datetime

# ✅ Dùng hệ thống template chung
from app.config.template_config import get_template_by_path

# ============================================================
# 🚀 Router
# ============================================================
report_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin - Reports"]
)

# ============================================================
# 📊 1️⃣ Tổng quan thống kê
# ============================================================
@report_router.get("/manage", response_class=HTMLResponse)
def manage_reports(request: Request, db: Session = Depends(get_db)):
    """Hiển thị tổng quan các thống kê hệ thống"""
    tpl = get_template_by_path(request.url.path)
    try:
        total_students = db.query(Enrollment).count()
        total_courses = db.query(Course).count()
        total_quizzes = db.query(QuizAttempt).count()
        total_reviews = db.query(CourseReview).count()
        completed_lessons = db.query(LessonProgress).count()

        summary = {
            "students": total_students,
            "courses": total_courses,
            "quizzes": total_quizzes,
            "reviews": total_reviews,
            "completed_lessons": completed_lessons,
        }

        return tpl.TemplateResponse(
            "reports/manage_reports.html",
            {"request": request, "summary": summary, "page_title": "📊 Báo cáo thống kê hệ thống"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy vấn báo cáo: {str(e)}")

# ============================================================
# 📈 2️⃣ Sinh báo cáo chi tiết
# ============================================================
@report_router.post("/generate", response_class=HTMLResponse)
def generate_report(
    request: Request,
    report_type: str = Form(...),
    db: Session = Depends(get_db)
):
    """Sinh báo cáo chi tiết theo loại"""
    tpl = get_template_by_path(request.url.path)
    try:
        if report_type == "course":
            data = db.query(Course).all()
        elif report_type == "enrollment":
            data = db.query(Enrollment).all()
        else:
            data = []

        return tpl.TemplateResponse(
            "reports/report_result.html",
            {
                "request": request,
                "data": data,
                "report_type": report_type,
                "total": len(data),
                "generated_at": datetime.now()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo báo cáo: {str(e)}")

# ============================================================
# 🗑️ 3️⃣ Xóa báo cáo (giả lập)
# ============================================================
@report_router.delete("/delete/{report_id}")
def delete_report(report_id: str):
    """Xóa báo cáo (giả lập)"""
    return {"message": f"✅ Đã xóa báo cáo {report_id} thành công"}
