from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin.course_category_service import (
    create_course_category,
    update_course_category,
    delete_course_category,
    get_all_course_categories,
    get_course_category_by_id,
)

# ===============================
# 🔧 Cấu hình router & template
# ===============================
category_router = APIRouter(prefix="/admin", tags=["Admin - Course Category"])

templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates"
)

# ===============================
# 📋 1. Danh sách danh mục
# ===============================
@category_router.get("/CourseCategory/manage", response_class=HTMLResponse)
async def manage_categories(request: Request, db: Session = Depends(get_db)):
    categories = get_all_course_categories(db)
    context = {"request": request, "categories": categories, "active_page": "course_category"}
    return templates.TemplateResponse("admin/CourseCategory/manage_categories.html", context)

# ===============================
# ➕ 2. Trang thêm danh mục
# ===============================
@category_router.get("/CourseCategory/create", response_class=HTMLResponse)
async def create_category_page(request: Request):
    return templates.TemplateResponse(
        "admin/CourseCategory/create.html",
        {"request": request, "active_page": "course_category"},
    )


@category_router.post("/CourseCategory/add")
async def add_category(
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        create_course_category(category_name, description, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center; margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/create'>← Quay lại</a></p>",
            status_code=400,
        )

# ===============================
# ✏️ 3. Trang chỉnh sửa danh mục
# ===============================
@category_router.get("/CourseCategory/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")
    return templates.TemplateResponse(
        "admin/CourseCategory/edit.html",
        {"request": request, "category": category, "active_page": "course_category"},
    )


@category_router.post("/CourseCategory/edit/{category_id}")
async def edit_category_action(
    category_id: str,
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        update_course_category(category_id, category_name, description, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center; margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/edit/{category_id}'>← Quay lại</a></p>",
            status_code=400,
        )

# ===============================
# ❌ 4. Trang xác nhận & xóa danh mục
# ===============================
@category_router.get("/CourseCategory/delete-confirm/{category_id}", response_class=HTMLResponse)
async def delete_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")
    return templates.TemplateResponse(
        "admin/CourseCategory/delete.html",
        {"request": request, "category": category, "active_page": "course_category"},
    )


@category_router.post("/CourseCategory/delete/{category_id}")
async def delete_category_action(category_id: str, db: Session = Depends(get_db)):
    try:
        delete_course_category(category_id, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center; margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/manage'>← Quay lại</a></p>",
            status_code=400,
        )
