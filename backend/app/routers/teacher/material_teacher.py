from fastapi import APIRouter, Request, Form, File, UploadFile, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi.templating import Jinja2Templates

from app.database.connection import get_db
from app.models.user import User
from app.models.course import Course
from app.services.teacher import material_service

# ==============================
# 🚀 Khởi tạo router
# ==============================
router = APIRouter(
    prefix="/teacher/materials",
    tags=["Teacher - Materials"]
)

# ==============================
# 📁 Cấu hình template
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/materials"
)
# ==============================
# 📋 Danh sách tài liệu
# ==============================
@router.get("/list", response_class=HTMLResponse)
async def list_materials(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị danh sách tài liệu mà giáo viên đã upload.
    """
    # 🔹 Lấy thông tin giáo viên đang đăng nhập (tạm hardcode)
    teacher_username = "gv_nguyenvanA"
    teacher = db.query(User).filter(User.username == teacher_username).first()
    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy giáo viên.</h3>", status_code=404)

    materials = material_service.list_materials(db, teacher.id)
    return templates.TemplateResponse(
        "list.html",
        {"request": request, "materials": materials}
    )


# ==============================
# 📂 Trang upload tài liệu
# ==============================
@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request, db: Session = Depends(get_db)):
    """
    Hiển thị form upload tài liệu cho khóa học của giáo viên.
    """
    teacher_username = "gv_nguyenvanA"  # ⚠️ sau này thay bằng session
    teacher = db.query(User).filter(User.username == teacher_username).first()

    courses = []
    if teacher:
        courses = db.query(Course).filter(Course.teacher_id == teacher.id).all()

    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "courses": courses}
    )


# ==============================
# 📤 Xử lý upload tài liệu
# ==============================
@router.post("/upload")
async def upload_material(
    request: Request,
    course_id: str = Form(...),
    material_type: str = Form("slide"),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Xử lý upload file và lưu metadata vào DB.
    """
    teacher_username = "gv_nguyenvanA"  # ⚠️ sau này thay bằng session
    teacher = db.query(User).filter(User.username == teacher_username).first()

    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy giáo viên.</h3>", status_code=404)

    result = await material_service.upload_material(
        db, teacher.id, course_id, material_type, title, description, file
    )
    if "error" in result:
        return HTMLResponse(f"<h3>{result['error']}</h3>", status_code=400)
    return RedirectResponse(url="/teacher/materials/list", status_code=303)


# ==============================
# 🗑️ Xóa tài liệu
# ==============================
@router.post("/delete/{material_id}")
async def delete_material(material_id: str, db: Session = Depends(get_db)):
    """
    Xóa file và bản ghi tương ứng trong DB.
    """
    teacher_username = "gv_nguyenvanA"
    teacher = db.query(User).filter(User.username == teacher_username).first()

    if not teacher:
        return HTMLResponse("<h3>Không tìm thấy giáo viên.</h3>", status_code=404)

    result = material_service.delete_material(db, teacher.id, material_id)
    if "error" in result:
        return HTMLResponse(f"<h3>{result['error']}</h3>", status_code=400)
    return RedirectResponse(url="/teacher/materials/list", status_code=303)
