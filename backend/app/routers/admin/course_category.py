from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Form, Depends, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.services.admin.course_category_service import (
    create_course_category,
    update_course_category,
    delete_course_category,
    get_all_course_categories,
    get_course_category_by_id,
)

category_router = APIRouter(
    prefix="/admin/CourseCategory",
    tags=["Admin - Course Category"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "course_category",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@category_router.get("/manage", response_class=HTMLResponse)
async def manage_categories(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    categories = get_all_course_categories(db)
    return render_template(
        request,
        "CourseCategory/manage_categories.html",
        {
            "categories": categories,
            "success": success,
            "error": error,
        }
    )


@category_router.get("/create", response_class=HTMLResponse)
async def create_category_page(request: Request):
    return render_template(
        request,
        "CourseCategory/create.html",
        {
            "form_data": {
                "category_name": "",
                "description": "",
            }
        }
    )


@category_router.post("/create", response_class=HTMLResponse)
async def add_category(
    request: Request,
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    form_data = {
        "category_name": category_name,
        "description": description or "",
    }

    try:
        create_course_category(db=db, category_name=category_name, description=description)
        message = quote("Tạo danh mục thành công.")
        return RedirectResponse(
            url=f"/admin/CourseCategory/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        return render_template(
            request,
            "CourseCategory/create.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except RuntimeError as e:
        return render_template(
            request,
            "CourseCategory/create.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@category_router.get("/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")

    return render_template(
        request,
        "CourseCategory/edit.html",
        {"category": category}
    )


@category_router.post("/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_action(
    category_id: str,
    request: Request,
    category_name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")

    try:
        update_course_category(
            db=db,
            category_id=category_id,
            category_name=category_name,
            description=description,
        )
        message = quote("Cập nhật danh mục thành công.")
        return RedirectResponse(
            url=f"/admin/CourseCategory/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        category.category_name = category_name
        category.description = description or ""
        return render_template(
            request,
            "CourseCategory/edit.html",
            {
                "category": category,
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except RuntimeError as e:
        category.category_name = category_name
        category.description = description or ""
        return render_template(
            request,
            "CourseCategory/edit.html",
            {
                "category": category,
                "error": str(e),
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@category_router.get("/delete-confirm/{category_id}", response_class=HTMLResponse)
async def delete_category_page(category_id: str, request: Request, db: Session = Depends(get_db)):
    category = get_course_category_by_id(category_id, db)
    if not category:
        raise HTTPException(status_code=404, detail="Danh mục không tồn tại.")

    return render_template(
        request,
        "CourseCategory/delete.html",
        {"category": category}
    )


@category_router.post("/delete/{category_id}")
async def delete_category_action(category_id: str, db: Session = Depends(get_db)):
    try:
        delete_course_category(db=db, category_id=category_id)
        message = quote("Xóa danh mục thành công.")
        return RedirectResponse(
            url=f"/admin/CourseCategory/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/CourseCategory/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except RuntimeError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/CourseCategory/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )