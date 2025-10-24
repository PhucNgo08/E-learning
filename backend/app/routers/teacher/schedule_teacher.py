from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.teacher import schedule_service

# =========================================================
# 🚀 Router
# =========================================================
router = APIRouter(
    prefix="/teacher/schedule",
    tags=["Teacher - Schedule"]
)

# =========================================================
# 🧭 Cấu hình templates
# =========================================================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# =========================================================
# 🗓️ 1️⃣ Lịch dạy theo tuần của giáo viên
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def view_schedule(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị lịch dạy của giáo viên (theo tuần)
    """
    # 🧩 Tạm thời: ID của giáo viên (lấy từ bảng users)
    # Sau này bạn có thể thay bằng Depends(get_current_user_id)
    teacher_id = "uuid-cua-giao-vien-trong-bang-users"

    # 🔹 Gọi service lấy dữ liệu
    schedule = schedule_service.get_teacher_schedule(db, teacher_id)

    # 🔹 Trả về template hiển thị
    return templates.TemplateResponse(
        "teacher/schedule/list.html",
        {"request": request, "schedule": schedule}
    )
