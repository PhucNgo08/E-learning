from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz_attempt import QuizAttempt
from app.models.course_review import CourseReview
from app.models.lesson_progress import LessonProgress
from datetime import datetime

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/reports"
)

report_router = APIRouter(
    prefix="/admin/reports",
    tags=["Admin - Reports"]
)


# 📊 Tổng quan thống kê
@report_router.get("/manage", response_class=HTMLResponse)
def manage_reports(request: Request, db: Session = Depends(get_db)):
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

        return templates.TemplateResponse(
            "manage_reports.html",
            {"request": request, "summary": summary}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy vấn báo cáo: {str(e)}")


# 📈 Sinh báo cáo chi tiết
@report_router.post("/generate", response_class=HTMLResponse)
def generate_report(report_type: str = Form(...), db: Session = Depends(get_db)):
    try:
        if report_type == "course":
            data = db.query(Course).all()
        elif report_type == "enrollment":
            data = db.query(Enrollment).all()
        else:
            data = []

        return templates.TemplateResponse(
            "report_result.html",
            {"request": None, "data": data, "report_type": report_type, "total": len(data)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo báo cáo: {str(e)}")


# 🗑️ Xóa báo cáo (giả lập)
@report_router.delete("/delete/{report_id}")
def delete_report(report_id: str):
    return {"message": f"Đã xóa báo cáo {report_id} thành công"}
