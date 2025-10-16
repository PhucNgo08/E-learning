from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import Course, Enrollment, Assignment
from app.dependencies import get_current_user_id

# ==============================
# ⚙️ Khởi tạo Router & Template
# ==============================
router = APIRouter(prefix="/student", tags=["Student Dashboard"])

# ⚠️ Quan trọng: trỏ đến thư mục templates GỐC
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)


# ==============================
# 🎓 Trang Dashboard Sinh viên
# ==============================
@router.get("/dashboard", response_class=HTMLResponse)
async def get_student_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Hiển thị bảng điều khiển chính của sinh viên.
    Bao gồm danh sách khóa học đã đăng ký và bài tập tương ứng.
    """

    # 🧩 Kiểm tra đăng nhập
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để truy cập bảng điều khiển."
        )

    # 📘 Lấy danh sách khóa học mà sinh viên đã ghi danh
    enrolled_courses = (
        db.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.user_id == user_id)
        .all()
    )

    # 📚 Lấy danh sách bài tập (Assignments) thuộc các khóa học đó
    course_ids = [c.id for c in enrolled_courses] if enrolled_courses else []
    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id.in_(course_ids))
        .all()
        if course_ids else []
    )

    # 🧭 Gửi dữ liệu sang template Dashboard
    return templates.TemplateResponse(
        "student/dashboard.html",  # ✅ Đúng path template
        {
            "request": request,
            "username": request.session.get("username"),  # 👤 Tên người dùng đăng nhập
            "active_page": "dashboard",                   # 🔖 Đánh dấu trang hiện tại trong sidebar
            "enrolled_courses": enrolled_courses,         # 📘 Danh sách khóa học đã đăng ký
            "assignments": assignments,                   # 📝 Danh sách bài tập
            "message": "Bạn chưa đăng ký khóa học nào." if not enrolled_courses else None
        },
    )
