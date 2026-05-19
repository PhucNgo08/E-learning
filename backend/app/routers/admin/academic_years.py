from typing import Optional
from datetime import datetime
import logging
from urllib.parse import quote

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.services.admin import academic_year_service
from app.models.academic_year import AcademicYear
from app.config.template_config import get_template_by_path

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/academic_years",
    tags=["Admin - Academic Years Management"],
    dependencies=[Depends(get_current_admin)],
)


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


# =========================================================
# 1) Danh sách năm học
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def list_academic_years(
    request: Request,
    success: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        years = academic_year_service.get_all_academic_years(db)
        return render_template(
            request,
            "academic_years/list.html",
            {
                "years": years,
                "success": success,
                "error": error,
            }
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi tải danh sách năm học")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải danh sách năm học."
        )


# =========================================================
# 2) Tạo năm học mới
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_form(request: Request):
    return render_template(
        request,
        "academic_years/create.html",
        {
            "form_data": {
                "year_code": "",
                "year_name": "",
                "start_year": "",
                "end_year": "",
                "is_active": True,
            }
        }
    )


@router.post("/create", response_class=HTMLResponse)
def create_academic_year(
    request: Request,
    year_code: str = Form(...),
    year_name: str = Form(...),
    start_year: int = Form(...),
    end_year: int = Form(...),
    is_active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    form_data = {
        "year_code": year_code.strip(),
        "year_name": year_name.strip(),
        "start_year": start_year,
        "end_year": end_year,
        "is_active": is_active is not None,
    }

    try:
        academic_year_service.create_academic_year(
            db=db,
            year_code=form_data["year_code"],
            year_name=form_data["year_name"],
            start_year=form_data["start_year"],
            end_year=form_data["end_year"],
            is_active=form_data["is_active"],
        )
        message = quote("Tạo năm học thành công.")
        return RedirectResponse(
            url=f"/admin/academic_years/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        return render_template(
            request,
            "academic_years/create.html",
            {
                "error": str(e),
                "form_data": form_data,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi tạo năm học")
        return render_template(
            request,
            "academic_years/create.html",
            {
                "error": "Đã xảy ra lỗi hệ thống khi tạo năm học.",
                "form_data": form_data,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =========================================================
# 3) Chỉnh sửa năm học
# =========================================================
@router.get("/edit/{year_id}", response_class=HTMLResponse)
def edit_form(request: Request, year_id: str, db: Session = Depends(get_db)):
    try:
        year = academic_year_service.get_academic_year_by_id(db, year_id)
        if not year:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học.")

        return render_template(
            request,
            "academic_years/edit.html",
            {"year": year}
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi tải form sửa năm học")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải thông tin năm học."
        )


@router.post("/edit/{year_id}", response_class=HTMLResponse)
def update_academic_year(
    request: Request,
    year_id: str,
    year_code: str = Form(...),
    year_name: str = Form(...),
    start_year: int = Form(...),
    end_year: int = Form(...),
    is_active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    form_data = {
        "id": year_id,
        "year_code": year_code.strip(),
        "year_name": year_name.strip(),
        "start_year": start_year,
        "end_year": end_year,
        "is_active": is_active is not None,
    }

    try:
        year = academic_year_service.get_academic_year_by_id(db, year_id)
        if not year:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học.")

        academic_year_service.update_academic_year(
            db=db,
            year_id=year_id,
            year_code=form_data["year_code"],
            year_name=form_data["year_name"],
            start_year=form_data["start_year"],
            end_year=form_data["end_year"],
            is_active=form_data["is_active"],
        )

        message = quote("Cập nhật năm học thành công.")
        return RedirectResponse(
            url=f"/admin/academic_years/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        return render_template(
            request,
            "academic_years/edit.html",
            {
                "year": form_data,
                "error": str(e),
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi cập nhật năm học")
        return render_template(
            request,
            "academic_years/edit.html",
            {
                "year": form_data,
                "error": "Đã xảy ra lỗi hệ thống khi cập nhật năm học.",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =========================================================
# 4) Xóa năm học
# =========================================================
@router.post("/delete/{year_id}")
def delete_academic_year(year_id: str, db: Session = Depends(get_db)):
    try:
        result = academic_year_service.delete_academic_year(db, year_id)
        if not result:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học cần xóa.")

        message = quote("Xóa năm học thành công.")
        return RedirectResponse(
            url=f"/admin/academic_years/list?success={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/academic_years/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi xóa năm học")
        message = quote("Không thể xóa năm học.")
        return RedirectResponse(
            url=f"/admin/academic_years/list?error={message}",
            status_code=status.HTTP_303_SEE_OTHER
        )


# =========================================================
# 5) Xem danh sách sinh viên theo năm học
# =========================================================
@router.get("/{year_id}/students", response_class=HTMLResponse)
def students_by_year(request: Request, year_id: str, db: Session = Depends(get_db)):
    try:
        year = db.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if not year:
            raise HTTPException(status_code=404, detail="Không tìm thấy năm học.")

        students = academic_year_service.get_students_by_academic_year(db, year_id)

        return render_template(
            request,
            "academic_years/students_by_year.html",
            {
                "year": year,
                "students": students,
            }
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Lỗi khi hiển thị sinh viên theo năm học")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải danh sách sinh viên."
        )