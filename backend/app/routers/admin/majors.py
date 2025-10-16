from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services import major_service
from app.services.course_category_service import get_all_categories  # 👈 thêm dòng này

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/majors"
)

router = APIRouter(
    prefix="/admin/majors",
    tags=["Admin - Majors Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách ngành học
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def list_majors(request: Request, db: Session = Depends(get_db)):
    majors = major_service.get_all_majors(db)
    return templates.TemplateResponse("list.html", {"request": request, "majors": majors})


# =========================================================
# ➕ 2️⃣ Tạo ngành học
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_major_form(request: Request, db: Session = Depends(get_db)):
    majors = major_service.get_all_majors(db)
    categories = get_all_categories(db)  # ✅ lấy danh sách khoa từ bảng course_categories
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "majors": majors, "categories": categories}
    )
@router.post("/create")
def create_major(
    major_code: str = Form(...),
    major_name: str = Form(...),
    faculty_name: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        major_service.create_major(db, major_code, major_name, faculty_name)
        return RedirectResponse(url="/admin/majors/list", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(f"<h3 style='color:red;text-align:center;margin-top:40px;'>⚠️ {e}</h3>", status_code=400)


# =========================================================
# ✏️ 3️⃣ Chỉnh sửa ngành học
# =========================================================
@router.get("/edit/{major_id}", response_class=HTMLResponse)
def edit_major_form(request: Request, major_id: str, db: Session = Depends(get_db)):
    major = major_service.get_major_by_id(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học.")
    return templates.TemplateResponse("edit.html", {"request": request, "major": major})


@router.post("/edit/{major_id}")
def update_major(
    major_id: str,
    major_code: str = Form(...),
    major_name: str = Form(...),
    faculty_name: str = Form(...),
    is_active: bool = Form(False),
    db: Session = Depends(get_db)
):
    updated = major_service.update_major(db, major_id, major_code, major_name, faculty_name, is_active)
    if not updated:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học để cập nhật.")
    return RedirectResponse(url="/admin/majors/list", status_code=303)


# =========================================================
# ❌ 4️⃣ Xóa ngành học
# =========================================================
@router.get("/delete/{major_id}", response_class=HTMLResponse)
def delete_major_form(request: Request, major_id: str, db: Session = Depends(get_db)):
    major = major_service.get_major_by_id(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học.")
    return templates.TemplateResponse("delete.html", {"request": request, "major": major})


@router.post("/delete/{major_id}")
def delete_major(major_id: str, db: Session = Depends(get_db)):
    success = major_service.delete_major(db, major_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học để xóa.")
    return RedirectResponse(url="/admin/majors/list", status_code=303)
