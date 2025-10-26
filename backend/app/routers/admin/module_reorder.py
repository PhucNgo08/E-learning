from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services import course_service
from pathlib import Path

# ==============================
# 🧭 Template Config
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/modules"
)


# ==============================
# 🚀 Router Init
# ==============================
router = APIRouter(
    prefix="/admin/modules",
    tags=["Admin - Module Management"]
)

# ==============================
# 🔁 Sắp xếp module
# ==============================
@router.get("/reorder", response_class=HTMLResponse)
def reorder_modules(request: Request, db: Session = Depends(get_db)):
    """Hiển thị giao diện sắp xếp thứ tự module"""
    try:
        courses = course_service.get_all_courses(db)
        return templates.TemplateResponse(
            "reorder.html",
            {"request": request, "courses": courses, "current_year": 2025}
        )
    except Exception as e:
        return HTMLResponse(f"<pre>Lỗi tải trang: {e}</pre>", status_code=500)
