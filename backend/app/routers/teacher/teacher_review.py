"""
==========================================================
🎓 ROUTER: Teacher - Reviews Management
Quản lý đánh giá khóa học mà giáo viên phụ trách
==========================================================
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.models.course import Course
from app.models.course_review import CourseReview as Review
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/reviews",
    tags=["Teacher - Reviews"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    templates = get_template_by_path(str(request.url.path))
    base_context = {
        "request": request,
        "now": datetime.now(),
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context, status_code=status_code)


def _teacher_courses(db: Session, teacher_id: str):
    return (
        db.query(Course)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc())
        .all()
    )


def _teacher_review_query(db: Session, teacher_id: str):
    return (
        db.query(Review)
        .join(Course, Review.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
    )


def _teacher_review_by_id(db: Session, teacher_id: str, review_id: str):
    return (
        db.query(Review)
        .join(Course, Review.course_id == Course.id)
        .filter(
            Review.id == review_id,
            Course.teacher_id == teacher_id
        )
        .first()
    )


@router.get("/", include_in_schema=False)
def redirect_root():
    return RedirectResponse("/teacher/reviews/manage", status_code=303)


@router.get("/manage", response_class=HTMLResponse)
def manage_reviews(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
    course_id: str | None = None,
    status: str | None = None,
    rating_min: float | None = None,
    rating_max: float | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    teacher = current_teacher
    courses = _teacher_courses(db, teacher.id)

    if not courses:
        return render_template(
            request,
            "reviews/manage.html",
            {
                "teacher": teacher,
                "reviews": [],
                "courses": [],
                "avg_rating": 0,
                "total_reviews": 0,
                "top_course": None,
                "rating_distribution": [0, 0, 0, 0, 0],
                "filters": {
                    "course_id": course_id,
                    "status": status,
                    "rating_min": rating_min,
                    "rating_max": rating_max,
                    "date_from": date_from,
                    "date_to": date_to,
                },
                "page_title": "⭐ Đánh giá khóa học",
            },
        )

    query = _teacher_review_query(db, teacher.id)

    if course_id:
        query = query.filter(Review.course_id == course_id)

    if status:
        query = query.filter(Review.status == status)

    if rating_min is not None:
        query = query.filter(Review.overall_rating >= rating_min)

    if rating_max is not None:
        query = query.filter(Review.overall_rating <= rating_max)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Review.created_at >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            # inclusive tới hết ngày
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Review.created_at < date_to_obj)
        except ValueError:
            pass

    reviews = query.order_by(Review.created_at.desc()).all()

    avg_rating = (
        query.with_entities(func.avg(Review.overall_rating)).scalar()
        or 0
    )

    total_reviews = (
        query.with_entities(func.count(Review.id)).scalar()
        or 0
    )

    # top course theo phạm vi filter hiện tại
    top_course_row = (
        db.query(Course, func.avg(Review.overall_rating).label("avg_rating"))
        .join(Review, Review.course_id == Course.id)
        .filter(Course.teacher_id == teacher.id)
    )

    if course_id:
        top_course_row = top_course_row.filter(Review.course_id == course_id)
    if status:
        top_course_row = top_course_row.filter(Review.status == status)
    if rating_min is not None:
        top_course_row = top_course_row.filter(Review.overall_rating >= rating_min)
    if rating_max is not None:
        top_course_row = top_course_row.filter(Review.overall_rating <= rating_max)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            top_course_row = top_course_row.filter(Review.created_at >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            top_course_row = top_course_row.filter(Review.created_at < date_to_obj)
        except ValueError:
            pass

    top_course_row = (
        top_course_row
        .group_by(Course.id)
        .order_by(func.avg(Review.overall_rating).desc())
        .first()
    )
    top_course = top_course_row[0] if top_course_row else None

    rating_distribution = [
        (
            query.with_entities(func.count(Review.id))
            .filter(
                and_(
                    Review.overall_rating >= i,
                    Review.overall_rating < i + 1,
                )
            )
            .scalar()
            or 0
        )
        for i in range(1, 6)
    ]

    return render_template(
        request,
        "reviews/manage.html",
        {
            "teacher": teacher,
            "reviews": reviews,
            "courses": courses,
            "avg_rating": round(float(avg_rating), 2),
            "total_reviews": total_reviews,
            "top_course": top_course,
            "rating_distribution": rating_distribution,
            "filters": {
                "course_id": course_id,
                "status": status,
                "rating_min": rating_min,
                "rating_max": rating_max,
                "date_from": date_from,
                "date_to": date_to,
            },
            "page_title": "⭐ Đánh giá khóa học",
        },
    )


@router.post("/approve/{review_id}")
def approve_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    review = _teacher_review_by_id(db, current_teacher.id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")

    review.status = "approved"
    review.moderated_by = current_teacher.id
    review.moderated_at = datetime.now()
    db.commit()

    return RedirectResponse("/teacher/reviews/manage", status_code=303)


@router.post("/reject/{review_id}")
def reject_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    review = _teacher_review_by_id(db, current_teacher.id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")

    review.status = "rejected"
    review.moderated_by = current_teacher.id
    review.moderated_at = datetime.now()
    db.commit()

    return RedirectResponse("/teacher/reviews/manage", status_code=303)


@router.get("/detail/{review_id}", response_class=HTMLResponse)
def review_detail(
    review_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    review = _teacher_review_by_id(db, current_teacher.id, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá này.")

    return render_template(
        request,
        "reviews/detail.html",
        {
            "teacher": current_teacher,
            "review": review,
            "page_title": f"Chi tiết đánh giá – {review.title or 'Không có tiêu đề'}",
        },
    )