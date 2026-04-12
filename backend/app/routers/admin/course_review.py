from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.course_review import CourseReview
from app.services.admin.review_stats_service import get_review_statistics
from app.config.template_config import get_template_by_path


review_router = APIRouter(
    prefix="/admin/reviews",
    tags=["Admin - Course Reviews"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "reviews",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def ensure_admin(request: Request):
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")


def get_review_or_404(db: Session, review_id: str):
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    return review


def get_course_display_name(review):
    course = getattr(review, "course", None)
    if not course:
        return "—"
    return getattr(course, "course_name", None) or getattr(course, "title", None) or "—"


def get_reviewer_display_name(review):
    user = getattr(review, "user", None) or getattr(review, "student", None)
    if not user:
        return "—"
    return (
        getattr(user, "full_name", None)
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or "—"
    )


def get_rating_value(review):
    value = getattr(review, "overall_rating", None)
    if value is None:
        value = getattr(review, "rating", None)
    return value or 0


@review_router.get("/manage", response_class=HTMLResponse)
def manage_reviews(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    try:
        reviews = db.query(CourseReview).order_by(CourseReview.created_at.desc()).all()

        total_reviews = len(reviews)
        avg_rating = (
            db.query(func.avg(CourseReview.overall_rating)).scalar()
            or 0
        )

        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        recent_count = (
            db.query(func.count(CourseReview.id))
            .filter(CourseReview.created_at >= start_of_month)
            .scalar()
            or 0
        )

        return render_template(
            request,
            "reviews/manage_reviews.html",
            {
                "reviews": reviews,
                "total_reviews": total_reviews,
                "avg_rating": round(float(avg_rating), 2),
                "recent_count": recent_count,
                "success": success,
                "error": error,
                "page_title": "📝 Quản lý đánh giá khóa học",
                "get_course_display_name": get_course_display_name,
                "get_reviewer_display_name": get_reviewer_display_name,
                "get_rating_value": get_rating_value,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy vấn đánh giá: {str(e)}") from e


@review_router.get("/view/{review_id}", response_class=HTMLResponse)
def view_review(request: Request, review_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    review = get_review_or_404(db, review_id)

    return render_template(
        request,
        "reviews/view_review.html",
        {
            "review": review,
            "page_title": "👁️ Chi tiết đánh giá",
            "course_name": get_course_display_name(review),
            "reviewer_name": get_reviewer_display_name(review),
            "rating_value": get_rating_value(review),
        }
    )


@review_router.get("/edit/{review_id}", response_class=HTMLResponse)
def edit_review_form(request: Request, review_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    review = get_review_or_404(db, review_id)

    return render_template(
        request,
        "reviews/edit_review.html",
        {
            "review": review,
            "error": None,
            "page_title": "✏️ Chỉnh sửa đánh giá",
            "course_name": get_course_display_name(review),
            "reviewer_name": get_reviewer_display_name(review),
            "rating_value": get_rating_value(review),
        }
    )


@review_router.post("/edit/{review_id}", response_class=HTMLResponse)
def update_review(
    request: Request,
    review_id: str,
    rating: int = Form(...),
    comment: str = Form(""),
    db: Session = Depends(get_db)
):
    ensure_admin(request)

    review = get_review_or_404(db, review_id)

    try:
        if rating < 1 or rating > 5:
            raise ValueError("Điểm đánh giá phải từ 1 đến 5.")

        review.overall_rating = rating
        review.comment = comment.strip() if comment else None
        review.updated_at = datetime.now()

        db.commit()
        db.refresh(review)

        message = quote("Cập nhật đánh giá thành công.")
        return RedirectResponse(
            url=f"/admin/reviews/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except ValueError as e:
        db.rollback()
        review.overall_rating = rating
        review.comment = comment
        return render_template(
            request,
            "reviews/edit_review.html",
            {
                "review": review,
                "error": str(e),
                "page_title": "✏️ Chỉnh sửa đánh giá",
                "course_name": get_course_display_name(review),
                "reviewer_name": get_reviewer_display_name(review),
                "rating_value": rating,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        db.rollback()
        review.overall_rating = rating
        review.comment = comment
        return render_template(
            request,
            "reviews/edit_review.html",
            {
                "review": review,
                "error": f"Lỗi khi cập nhật đánh giá: {str(e)}",
                "page_title": "✏️ Chỉnh sửa đánh giá",
                "course_name": get_course_display_name(review),
                "reviewer_name": get_reviewer_display_name(review),
                "rating_value": rating,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@review_router.get("/delete/{review_id}", response_class=HTMLResponse)
def confirm_delete(request: Request, review_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    review = get_review_or_404(db, review_id)

    return render_template(
        request,
        "reviews/delete_review.html",
        {
            "review": review,
            "page_title": "🗑️ Xóa đánh giá",
            "course_name": get_course_display_name(review),
            "reviewer_name": get_reviewer_display_name(review),
            "rating_value": get_rating_value(review),
        }
    )


@review_router.post("/delete/{review_id}")
def delete_review(request: Request, review_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    review = get_review_or_404(db, review_id)

    try:
        db.delete(review)
        db.commit()

        message = quote("Xóa đánh giá thành công.")
        return RedirectResponse(
            url=f"/admin/reviews/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        db.rollback()
        message = quote(f"Lỗi khi xóa đánh giá: {str(e)}")
        return RedirectResponse(
            url=f"/admin/reviews/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )


@review_router.get("/statistics/{course_id}", response_class=HTMLResponse)
def review_statistics(request: Request, course_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    try:
        data = get_review_statistics(db, course_id)

        return render_template(
            request,
            "reviews/statistics.html",
            {
                "review_data": data.get("star_distribution", [0, 0, 0, 0, 0]),
                "avg_rating": data.get("avg_rating", 0),
                "course_id": course_id,
                "page_title": "⭐ Thống kê đánh giá khóa học",
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải thống kê đánh giá: {str(e)}") from e