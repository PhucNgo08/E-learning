from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Form, Depends, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.admin.course_section_service import (
    create_section,
    update_section,
    delete_section,
    get_all_sections,
    get_section_by_id,
)
from app.models.course import Course
from app.config.template_config import get_template_by_path


section_router = APIRouter(
    prefix="/admin/sections",
    tags=["Admin - Course Section Management"]
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
        "active_page": "sections",
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def ensure_admin(request: Request):
    if request.session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập")


def get_courses(db: Session):
    return db.query(Course).order_by(Course.course_name.asc()).all()


@section_router.get("/manage", response_class=HTMLResponse)
async def manage_sections(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    ensure_admin(request)
    sections = get_all_sections(db)
    return render_template(
        request,
        "Sections/manage.html",
        {
            "sections": sections,
            "success": success,
            "error": error,
            "page_title": "📚 Quản lý học phần",
        },
    )


@section_router.get("/create", response_class=HTMLResponse)
async def create_section_form(request: Request, db: Session = Depends(get_db)):
    ensure_admin(request)
    return render_template(
        request,
        "Sections/create.html",
        {
            "courses": get_courses(db),
            "form_data": {
                "section_code": "",
                "section_name": "",
                "course_id": "",
                "max_students": 50,
                "location": "",
                "schedule_info": "",
            },
            "error": None,
        },
    )


@section_router.post("/create", response_class=HTMLResponse)
async def add_section(
    request: Request,
    section_code: str = Form(...),
    section_name: str = Form(...),
    course_id: str = Form(...),
    max_students: int = Form(50),
    location: str = Form(""),
    schedule_info: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    form_data = {
        "section_code": section_code,
        "section_name": section_name,
        "course_id": course_id,
        "max_students": max_students,
        "location": location,
        "schedule_info": schedule_info,
    }

    try:
        create_section(
            db=db,
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            location=location,
            schedule_info=schedule_info,
        )
        message = quote("Tạo học phần thành công.")
        return RedirectResponse(
            url=f"/admin/sections/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return render_template(
            request,
            "Sections/create.html",
            {
                "courses": get_courses(db),
                "form_data": form_data,
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "Sections/create.html",
            {
                "courses": get_courses(db),
                "form_data": form_data,
                "error": f"Lỗi khi tạo học phần: {str(e)}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@section_router.get("/edit/{section_id}", response_class=HTMLResponse)
async def edit_section_form(request: Request, section_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    section = get_section_by_id(db, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Không tìm thấy học phần.")

    return render_template(
        request,
        "Sections/edit.html",
        {
            "section": section,
            "courses": get_courses(db),
            "error": None,
        },
    )


@section_router.post("/edit/{section_id}", response_class=HTMLResponse)
async def edit_section(
    request: Request,
    section_id: str,
    section_code: str = Form(...),
    section_name: str = Form(...),
    course_id: str = Form(...),
    max_students: int = Form(50),
    location: str = Form(""),
    schedule_info: str = Form(""),
    db: Session = Depends(get_db),
):
    ensure_admin(request)

    section = get_section_by_id(db, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Không tìm thấy học phần.")

    try:
        update_section(
            db=db,
            section_id=section_id,
            section_code=section_code,
            section_name=section_name,
            course_id=course_id,
            max_students=max_students,
            location=location,
            schedule_info=schedule_info,
        )
        message = quote("Cập nhật học phần thành công.")
        return RedirectResponse(
            url=f"/admin/sections/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        section.section_code = section_code
        section.section_name = section_name
        section.course_id = course_id
        section.max_students = max_students
        section.location = location
        section.schedule_info = schedule_info
        return render_template(
            request,
            "Sections/edit.html",
            {
                "section": section,
                "courses": get_courses(db),
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        section.section_code = section_code
        section.section_name = section_name
        section.course_id = course_id
        section.max_students = max_students
        section.location = location
        section.schedule_info = schedule_info
        return render_template(
            request,
            "Sections/edit.html",
            {
                "section": section,
                "courses": get_courses(db),
                "error": f"Lỗi khi cập nhật học phần: {str(e)}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@section_router.get("/delete/{section_id}", response_class=HTMLResponse)
async def delete_section_confirm(request: Request, section_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    section = get_section_by_id(db, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Không tìm thấy học phần.")

    return render_template(
        request,
        "Sections/delete.html",
        {
            "section": section,
        },
    )


@section_router.post("/delete/{section_id}")
async def delete_section_route(request: Request, section_id: str, db: Session = Depends(get_db)):
    ensure_admin(request)

    try:
        delete_section(db=db, section_id=section_id)
        message = quote("Xóa học phần thành công.")
        return RedirectResponse(
            url=f"/admin/sections/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/sections/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi xóa học phần: {str(e)}")
        return RedirectResponse(
            url=f"/admin/sections/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )