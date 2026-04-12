"""
==========================================================
🧩 ROUTER: Admin - Quiz Template Management
Quản lý mẫu quiz trong khu vực admin
==========================================================
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.admin import quiz_template_service
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin

router = APIRouter(
    prefix="/admin/quiz-template",
    tags=["Admin - Quiz Template Management"]
)


def render_template(
    request: Request,
    template_name: str,
    context: dict,
    status_code: int = 200,
):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "page_title": "Quiz Template Management",
        "active_page": "quiz_template",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


# ============================================================
# 📋 Danh sách Quiz Templates
# ============================================================
@router.get("/list", response_class=HTMLResponse)
def list_templates(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    templates = quiz_template_service.get_all_with_creator(db)

    return render_template(
        request,
        "quiz_template/list.html",
        {
            "templates": templates,
            "page_title": "Danh sách Quiz Template",
        }
    )


# ============================================================
# ➕ Form tạo mới
# ============================================================
@router.get("/create", response_class=HTMLResponse)
def create_form(
    request: Request,
    current_user=Depends(get_current_admin),
):
    return render_template(
        request,
        "quiz_template/create.html",
        {
            "form_data": {
                "name": "",
                "description": "",
                "rules": "",
            },
            "error_message": None,
            "page_title": "Tạo Quiz Template",
        }
    )


# ============================================================
# ➕ Xử lý tạo template mới
# ============================================================
@router.post("/create", response_class=HTMLResponse)
def create_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    rules: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    name = (name or "").strip()
    description = (description or "").strip()
    rules = (rules or "").strip()

    form_data = {
        "name": name,
        "description": description,
        "rules": rules,
    }

    if not name:
        return render_template(
            request,
            "quiz_template/create.html",
            {
                "form_data": form_data,
                "error_message": "Tên template không được để trống.",
                "page_title": "Tạo Quiz Template",
            },
            status_code=400,
        )

    if not rules:
        return render_template(
            request,
            "quiz_template/create.html",
            {
                "form_data": form_data,
                "error_message": "Rules không được để trống.",
                "page_title": "Tạo Quiz Template",
            },
            status_code=400,
        )

    try:
        quiz_template_service.create(
            db=db,
            name=name,
            description=description,
            rules=rules,
            created_by=current_user.id,
        )
        return RedirectResponse("/admin/quiz-template/list", status_code=303)

    except Exception as e:
        return render_template(
            request,
            "quiz_template/create.html",
            {
                "form_data": form_data,
                "error_message": f"Lỗi khi tạo template: {e}",
                "page_title": "Tạo Quiz Template",
            },
            status_code=500,
        )


# ============================================================
# ✏️ Form sửa Template
# ============================================================
@router.get("/edit/{template_id}", response_class=HTMLResponse)
def edit_form(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    template = quiz_template_service.get_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Không tìm thấy template")

    return render_template(
        request,
        "quiz_template/edit.html",
        {
            "template": template,
            "error_message": None,
            "page_title": "Chỉnh sửa Quiz Template",
        }
    )


# ============================================================
# ✏️ Xử lý sửa Template
# ============================================================
@router.post("/edit/{template_id}", response_class=HTMLResponse)
def update_template(
    template_id: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    rules: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    name = (name or "").strip()
    description = (description or "").strip()
    rules = (rules or "").strip()

    template = quiz_template_service.get_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Không tìm thấy template")

    if not name:
        template.name = name
        template.description = description
        template.rules = rules
        return render_template(
            request,
            "quiz_template/edit.html",
            {
                "template": template,
                "error_message": "Tên template không được để trống.",
                "page_title": "Chỉnh sửa Quiz Template",
            },
            status_code=400,
        )

    if not rules:
        template.name = name
        template.description = description
        template.rules = rules
        return render_template(
            request,
            "quiz_template/edit.html",
            {
                "template": template,
                "error_message": "Rules không được để trống.",
                "page_title": "Chỉnh sửa Quiz Template",
            },
            status_code=400,
        )

    try:
        updated = quiz_template_service.update(
            db=db,
            template_id=template_id,
            name=name,
            description=description,
            rules=rules,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy template")

        return RedirectResponse("/admin/quiz-template/list", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        template.name = name
        template.description = description
        template.rules = rules
        return render_template(
            request,
            "quiz_template/edit.html",
            {
                "template": template,
                "error_message": f"Lỗi khi cập nhật template: {e}",
                "page_title": "Chỉnh sửa Quiz Template",
            },
            status_code=500,
        )


# ============================================================
# 🗑️ Xác nhận xóa
# ============================================================
@router.get("/delete/{template_id}", response_class=HTMLResponse)
def confirm_delete(
    template_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    template = quiz_template_service.get_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Không tìm thấy template")

    return render_template(
        request,
        "quiz_template/delete.html",
        {
            "template": template,
            "page_title": "Xóa Quiz Template",
        }
    )


# ============================================================
# 🗑️ Thực hiện xóa
# ============================================================
@router.post("/delete/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    try:
        ok = quiz_template_service.delete(db, template_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Không tìm thấy template")

        return RedirectResponse("/admin/quiz-template/list", status_code=303)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa template: {e}")