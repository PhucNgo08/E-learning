from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.admin import major_service, course_category_service
from app.config.template_config import get_template_by_path
from app.dependencies.auth import get_current_admin


router = APIRouter(
    prefix="/admin/majors",
    tags=["Admin - Majors Management"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "majors",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


@router.get("/list", response_class=HTMLResponse)
def list_majors(
    request: Request,
    q: str | None = Query(None),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    majors = major_service.get_all_majors(db, q=q)

    return render_template(
        request,
        "majors/list.html",
        {
            "majors": majors,
            "q": q or "",
            "success": success,
            "error": error,
            "page_title": "📚 Danh sách ngành học",
        }
    )


@router.get("/create", response_class=HTMLResponse)
def create_major_form(
    request: Request,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    categories = course_category_service.get_all_course_categories(db)

    return render_template(
        request,
        "majors/create.html",
        {
            "categories": categories,
            "form_data": {
                "major_code": "",
                "major_name": "",
                "faculty_name": "",
            },
            "error": None,
            "page_title": "➕ Thêm ngành học",
        }
    )


@router.post("/create", response_class=HTMLResponse)
def create_major(
    request: Request,
    major_code: str = Form(...),
    major_name: str = Form(...),
    faculty_name: str = Form(""),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    form_data = {
        "major_code": major_code,
        "major_name": major_name,
        "faculty_name": faculty_name,
    }

    try:
        major_service.create_major(db, major_code, major_name, faculty_name)
        message = quote("Tạo ngành học thành công.")
        return RedirectResponse(
            url=f"/admin/majors/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except ValueError as e:
        categories = course_category_service.get_all_course_categories(db)
        return render_template(
            request,
            "majors/create.html",
            {
                "categories": categories,
                "form_data": form_data,
                "error": str(e),
                "page_title": "➕ Thêm ngành học",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        categories = course_category_service.get_all_course_categories(db)
        return render_template(
            request,
            "majors/create.html",
            {
                "categories": categories,
                "form_data": form_data,
                "error": f"Lỗi không xác định: {str(e)}",
                "page_title": "➕ Thêm ngành học",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/edit/{major_id}", response_class=HTMLResponse)
def edit_major_form(
    request: Request,
    major_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    major = major_service.get_major_by_id(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học.")

    categories = course_category_service.get_all_course_categories(db)

    return render_template(
        request,
        "majors/edit.html",
        {
            "major": major,
            "categories": categories,
            "error": None,
            "page_title": "✏️ Cập nhật ngành học",
        }
    )


@router.post("/edit/{major_id}", response_class=HTMLResponse)
def update_major(
    request: Request,
    major_id: str,
    major_code: str = Form(...),
    major_name: str = Form(...),
    faculty_name: str = Form(""),
    is_active: bool = Form(False),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    major = major_service.get_major_by_id(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học để cập nhật.")

    try:
        major_service.update_major(
            db=db,
            major_id=major_id,
            major_code=major_code,
            major_name=major_name,
            faculty_name=faculty_name,
            is_active=is_active,
        )
        message = quote("Cập nhật ngành học thành công.")
        return RedirectResponse(
            url=f"/admin/majors/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    except ValueError as e:
        major.major_code = major_code
        major.major_name = major_name
        major.faculty_name = faculty_name
        major.is_active = is_active

        categories = course_category_service.get_all_course_categories(db)
        return render_template(
            request,
            "majors/edit.html",
            {
                "major": major,
                "categories": categories,
                "error": str(e),
                "page_title": "✏️ Cập nhật ngành học",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        major.major_code = major_code
        major.major_name = major_name
        major.faculty_name = faculty_name
        major.is_active = is_active

        categories = course_category_service.get_all_course_categories(db)
        return render_template(
            request,
            "majors/edit.html",
            {
                "major": major,
                "categories": categories,
                "error": f"Lỗi khi cập nhật ngành học: {str(e)}",
                "page_title": "✏️ Cập nhật ngành học",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/delete/{major_id}", response_class=HTMLResponse)
def delete_major_form(
    request: Request,
    major_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    major = major_service.get_major_by_id(db, major_id)
    if not major:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngành học.")

    return render_template(
        request,
        "majors/delete.html",
        {
            "major": major,
            "page_title": "🗑 Xóa ngành học",
        }
    )


@router.post("/delete/{major_id}")
def delete_major(
    major_id: str,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    del current_admin

    try:
        major_service.delete_major(db, major_id)
        message = quote("Xóa ngành học thành công.")
        return RedirectResponse(
            url=f"/admin/majors/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/majors/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi xóa ngành học: {str(e)}")
        return RedirectResponse(
            url=f"/admin/majors/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )