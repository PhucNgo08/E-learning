from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.connection import get_db
from app.models.course import Course
from app.models.course_review import CourseReview as Review
from app.dependencies.auth import get_current_teacher
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/reviews"
)

router = APIRouter(prefix="/teacher/reviews", tags=["Teacher - Reviews"])


@router.get("/manage", response_class=HTMLResponse)
def manage_reviews(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    # 📋 Lấy danh sách đánh giá của giáo viên hiện tại
    reviews = (
        db.query(Review)
        .join(Course)
        .filter(Course.teacher_id == current_teacher.id)
        .all()
    )

    courses = db.query(Course).filter(Course.teacher_id == current_teacher.id).all()

    # 📊 Tính điểm trung bình
    avg_rating = db.query(func.avg(Review.overall_rating)).scalar()
    total_reviews = db.query(Review).count()

    # 🏆 Khóa học có điểm cao nhất (GROUP BY để tránh lỗi MySQL)
    top_course = (
        db.query(Course, func.avg(Review.overall_rating).label("avg_rating"))
        .join(Review, Review.course_id == Course.id)
        .group_by(Course.id)
        .order_by(func.avg(Review.overall_rating).desc())
        .first()
    )
    top_course = top_course[0] if top_course else None

    # 📈 Phân bố điểm 1–5
    rating_distribution = [
        db.query(Review).filter(
            Review.overall_rating >= i,
            Review.overall_rating < i + 1
        ).count()
        for i in range(1, 6)
    ]

    # 📦 Render giao diện
    return templates.TemplateResponse(
        "manage.html",
        {
            "request": request,
            "reviews": reviews,
            "courses": courses,
            "avg_rating": round(float(avg_rating or 0), 2),
            "total_reviews": total_reviews,
            "top_course": top_course,
            "rating_distribution": rating_distribution,
        },
    )
