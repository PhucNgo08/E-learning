from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.course_review import CourseReview
from app.models.course import Course
from datetime import datetime
from pathlib import Path

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/reviews"
)

router = APIRouter(prefix="/teacher/reviews", tags=["Teacher - Reviews"])

@router.get("/manage", response_class=HTMLResponse)
def manage_reviews(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "teacher":
        return RedirectResponse(url="/auth/login", status_code=303)

    reviews = (
        db.query(CourseReview)
        .join(Course, Course.id == CourseReview.course_id)
        .filter(Course.teacher_id == user_id)
        .order_by(CourseReview.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "manage.html",
        {"request": request, "reviews": reviews, "now": datetime.now()},
    )
