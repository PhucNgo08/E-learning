from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.database.connection import get_db
from app.models.course_review import CourseReview
from app.services.admin.review_stats_service import get_review_statistics

# ==============================
# 🧭 Cấu hình Template
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates( directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/reviews" )
# ==============================
# 🚀 Khởi tạo Router
# ==============================
review_router = APIRouter(
    prefix="/admin/reviews",
    tags=["Admin - Course Reviews"]
)

# =========================================================
# 📋 1️⃣ Danh sách đánh giá
# =========================================================
@review_router.get("/manage", response_class=HTMLResponse)
def manage_reviews(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách tất cả các đánh giá khóa học"""
    try:
        reviews = db.query(CourseReview).order_by(CourseReview.created_at.desc()).all()
        return templates.TemplateResponse(
            "manage_reviews.html",
            {"request": request, "reviews": reviews}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi truy vấn đánh giá: {str(e)}")

# =========================================================
# 📝 2️⃣ Xem chi tiết 1 đánh giá
# =========================================================
@review_router.get("/view/{review_id}", response_class=HTMLResponse)
def view_review(request: Request, review_id: str, db: Session = Depends(get_db)):
    """Xem chi tiết một đánh giá"""
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    
    return templates.TemplateResponse("view_review.html", {"request": request, "review": review})

# =========================================================
# ✏️ 3️⃣ Form chỉnh sửa đánh giá
# =========================================================
@review_router.get("/edit/{review_id}", response_class=HTMLResponse)
def edit_review_form(request: Request, review_id: str, db: Session = Depends(get_db)):
    """Hiển thị form chỉnh sửa đánh giá"""
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    
    return templates.TemplateResponse("edit_review.html", {"request": request, "review": review})

# =========================================================
# 💾 4️⃣ Cập nhật đánh giá
# =========================================================
@review_router.post("/edit/{review_id}")
def update_review(
    review_id: str,
    rating: int = Form(...),
    comment: str = Form(...),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin đánh giá"""
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    try:
        review.overall_rating = rating
        review.comment = comment
        review.updated_at = datetime.now()
        db.commit()
        db.refresh(review)
        return RedirectResponse("/admin/reviews/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật đánh giá: {str(e)}")

# =========================================================
# 🗑️ 5️⃣ Xóa đánh giá
# =========================================================
@review_router.get("/delete/{review_id}", response_class=HTMLResponse)
def confirm_delete(request: Request, review_id: str, db: Session = Depends(get_db)):
    """Hiển thị xác nhận xóa đánh giá"""
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    return templates.TemplateResponse("delete_review.html", {"request": request, "review": review})

@review_router.post("/delete/{review_id}")
def delete_review(review_id: str, db: Session = Depends(get_db)):
    """Xóa đánh giá khỏi cơ sở dữ liệu"""
    review = db.query(CourseReview).filter(CourseReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá.")
    try:
        db.delete(review)
        db.commit()
        return RedirectResponse("/admin/reviews/manage", status_code=303)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa đánh giá: {str(e)}")

# =========================================================
# 📊 6️⃣ Thống kê đánh giá khóa học (biểu đồ sao)
# =========================================================
@review_router.get("/statistics/{course_id}", response_class=HTMLResponse)
def review_statistics(request: Request, course_id: str, db: Session = Depends(get_db)):
    """Hiển thị biểu đồ thống kê đánh giá theo khóa học"""
    try:
        data = get_review_statistics(db, course_id)
        return templates.TemplateResponse(
            "statistics.html",
            {
                "request": request,
                "review_data": data["star_distribution"],
                "avg_rating": data["avg_rating"],
                "course_id": course_id
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải thống kê đánh giá: {str(e)}")
