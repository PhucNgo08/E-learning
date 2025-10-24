from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.teacher import statistics_service

# =========================================================
# 🚀 Router
# =========================================================
router = APIRouter(
    prefix="/teacher/statistics",
    tags=["Teacher - Statistics"]
)

# =========================================================
# 🧭 Cấu hình templates
# =========================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# =========================================================
# 📊 1️⃣ Trang thống kê giáo viên
# =========================================================
@router.get("/index", response_class=HTMLResponse)
def teacher_statistics(request: Request, db: Session = Depends(get_db)):
    """Hiển thị trang thống kê cho giáo viên"""
    data = statistics_service.get_teacher_statistics(db)

    return templates.TemplateResponse(
        "teacher/statistics/index.html",
        {"request": request, "data": data}
    )
