from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.admin.course_category_service import (
    create_course_category,
    update_course_category,
    delete_course_category,
    get_all_course_categories,
    get_course_category_by_id,
)
# ✅ Import hệ thống template dùng chung
from app.config.template_config import get_template_by_path

# ============================================================
# 🚀 Router
# ============================================================
category_router = APIRouter(
    prefix="/admin/CourseCategory",
    tags=["Admin - Course Category"]
)

# ============================================================
# 📋 1️⃣ Danh sách danh mục
# ============================================================
@category_router.get("/manage", response_class=HTMLResponse)
async def manage_categories(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    categories = get_all_course_categories(db)
    return tpl.TemplateResponse(
        "CourseCategory/manage_categories.html",
        {"request": request, "categories": categories, "active_page": "course_category"}
    )

# ============================================================
# ➕ 2️⃣ Trang thêm danh mục
# ============================================================
@category_router.get("/create", response_class=HTMLResponse)
async def create_category_page(request: Request):
    tpl = get_template_by_path(request.url.path)
    return tpl.TemplateResponse(
        "CourseCategory/create.html",
        {"request": request, "active_page": "course_category"}
    )

@category_router.post("/add")
async def add_category(
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        create_course_category(category_name, description, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center;margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/create'>← Quay lại</a></p>",
            status_code=400
        )

# ============================================================
# ✏️ 3️⃣ Trang chỉnh sửa danh mục
# ============================================================
@category_router.get("/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")
    return tpl.TemplateResponse(
        "CourseCategory/edit.html",
        {"request": request, "category": category, "active_page": "course_category"}
    )

@category_router.post("/edit/{category_id}")
async def edit_category_action(
    category_id: str,
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        update_course_category(category_id, category_name, description, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center;margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/edit/{category_id}'>← Quay lại</a></p>",
            status_code=400
        )

# ============================================================
# ❌ 4️⃣ Trang xác nhận & xóa danh mục
# ============================================================
@category_router.get("/delete-confirm/{category_id}", response_class=HTMLResponse)
async def delete_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")
    return tpl.TemplateResponse(
        "CourseCategory/delete.html",
        {"request": request, "category": category, "active_page": "course_category"}
    )

@category_router.post("/delete/{category_id}")
async def delete_category_action(category_id: str, db: Session = Depends(get_db)):
    try:
        delete_course_category(category_id, db)
        return RedirectResponse(url="/admin/CourseCategory/manage", status_code=303)
    except RuntimeError as e:
        return HTMLResponse(
            f"<h3 style='color:red; text-align:center;margin-top:40px;'>⚠️ {e}</h3>"
            f"<p style='text-align:center;'><a href='/admin/CourseCategory/manage'>← Quay lại</a></p>",
            status_code=400
        )
