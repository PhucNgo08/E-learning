from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.dependencies.auth import get_current_admin
from app.models.academic_year import AcademicYear
from app.models.class_enrollment import ClassEnrollment
from app.models.major import Major
from app.models.rbac import Role
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.admin.class_management_service import (
    create_class,
    delete_class,
    get_all_classes,
    get_class_by_id,
    update_class,
)
from app.services.admin.enrollment_management_service import (
    add_student_to_class,
    remove_student_from_class,
)

ACTIVE_CLASS_ENROLLMENT_STATUSES = {"approved", "active"}

class_router = APIRouter(prefix="/admin/Class", tags=["Admin - Class Management"])


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Định dạng ngày không hợp lệ. Vui lòng dùng YYYY-MM-DD.")


def _display_name_from_user(user) -> str:
    if not user:
        return "Chưa phân công"
    if getattr(user, "full_name", None):
        return user.full_name
    user_profile = getattr(user, "user_profile", None)
    if user_profile and getattr(user_profile, "full_name", None):
        return user_profile.full_name
    return getattr(user, "username", None) or getattr(user, "email", None) or "Không rõ"


def _get_teacher_options(db: Session):
    rows = (
        db.query(
            User.id.label("id"),
            func.coalesce(UserProfile.full_name, User.username).label("name"),
        )
        .join(User.roles)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .filter(Role.role_code == "teacher")
        .order_by(func.coalesce(UserProfile.full_name, User.username).asc())
        .all()
    )
    return [{"id": r.id, "name": r.name} for r in rows]


def _get_class_list_view(db: Session):
    classes = get_all_classes(db)
    result = []

    for c in classes:
        result.append(
            {
                "id": c.id,
                "class_code": c.class_code,
                "class_name": c.class_name,
                "major_name": c.major.major_name if getattr(c, "major", None) else "—",
                "academic_year_name": c.academic_year.year_name if getattr(c, "academic_year", None) else "—",
                "teacher_name": _display_name_from_user(getattr(c, "homeroom_teacher", None)),
                "current_students": c.current_students or 0,
                "max_students": c.max_students or 0,
                "status": c.status or "planning",
            }
        )

    return result


def _get_students_in_class_view(db: Session, class_id: str):
    rows = (
        db.query(
            User.id.label("id"),
            func.coalesce(UserProfile.full_name, User.username).label("full_name"),
            User.email.label("email"),
            StudentProfile.mssv.label("mssv"),
        )
        .select_from(ClassEnrollment)
        .join(User, ClassEnrollment.student_id == User.id)
        .join(User.roles)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.enrollment_status.in_(ACTIVE_CLASS_ENROLLMENT_STATUSES),
            Role.role_code == "student",
        )
        .order_by(func.coalesce(UserProfile.full_name, User.username).asc())
        .all()
    )

    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "email": r.email,
            "mssv": r.mssv,
        }
        for r in rows
    ]


def _get_available_students_view(db: Session, class_id: str):
    enrolled_ids = [
        row[0]
        for row in (
            db.query(ClassEnrollment.student_id)
            .filter(ClassEnrollment.class_id == class_id)
            .all()
        )
    ]

    query = (
        db.query(
            User.id.label("id"),
            func.coalesce(UserProfile.full_name, User.username).label("full_name"),
            User.email.label("email"),
            StudentProfile.mssv.label("mssv"),
        )
        .join(User.roles)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .filter(Role.role_code == "student")
    )

    if enrolled_ids:
        query = query.filter(~User.id.in_(enrolled_ids))

    rows = query.order_by(func.coalesce(UserProfile.full_name, User.username).asc()).all()

    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "email": r.email,
            "mssv": r.mssv,
        }
        for r in rows
    ]


def _load_form_options(db: Session):
    return {
        "majors": db.query(Major).order_by(Major.major_name.asc()).all(),
        "academic_years": db.query(AcademicYear).order_by(AcademicYear.start_year.desc()).all(),
        "teachers": _get_teacher_options(db),
    }


@class_router.get("/manage", response_class=HTMLResponse)
def manage_classes(
    request: Request,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    classes = _get_class_list_view(db)
    return render_template(
        request,
        "Class/manage.html",
        {
            "classes": classes,
            "success": success,
            "error": error,
            "admin": admin,
        },
    )


@class_router.get("/create", response_class=HTMLResponse)
def create_class_form(request: Request, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    options = _load_form_options(db)
    return render_template(
        request,
        "Class/create.html",
        {
            **options,
            "form_data": {
                "class_code": "",
                "class_name": "",
                "class_type": "official",
                "academic_year_id": "",
                "major_id": "",
                "homeroom_teacher_id": "",
                "grade_level": "",
                "max_students": 50,
                "start_date": "",
                "end_date": "",
                "enrollment_start": "",
                "enrollment_end": "",
                "status": "planning",
            },
            "admin": admin,
        },
    )


@class_router.post("/create", response_class=HTMLResponse)
def add_class(
    request: Request,
    class_code: str = Form(...),
    class_name: str = Form(...),
    class_type: str = Form("official"),
    academic_year_id: str = Form(""),
    major_id: str = Form(""),
    homeroom_teacher_id: str = Form(""),
    grade_level: int | None = Form(None),
    max_students: int = Form(50),
    start_date: str = Form(""),
    end_date: str = Form(""),
    enrollment_start: str = Form(""),
    enrollment_end: str = Form(""),
    status_value: str = Form("planning", alias="status"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    form_data = {
        "class_code": class_code,
        "class_name": class_name,
        "class_type": class_type,
        "academic_year_id": academic_year_id,
        "major_id": major_id,
        "homeroom_teacher_id": homeroom_teacher_id,
        "grade_level": grade_level,
        "max_students": max_students,
        "start_date": start_date,
        "end_date": end_date,
        "enrollment_start": enrollment_start,
        "enrollment_end": enrollment_end,
        "status": status_value,
    }

    options = _load_form_options(db)

    try:
        create_class(
            db=db,
            class_code=class_code,
            class_name=class_name,
            class_type=class_type,
            academic_year_id=academic_year_id or None,
            major_id=major_id or None,
            grade_level=grade_level,
            max_students=max_students,
            homeroom_teacher_id=homeroom_teacher_id or None,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
            enrollment_start=_parse_date(enrollment_start),
            enrollment_end=_parse_date(enrollment_end),
            status=status_value,
        )

        message = quote("Tạo lớp học thành công.")
        return RedirectResponse(
            url=f"/admin/Class/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return render_template(
            request,
            "Class/create.html",
            {
                **options,
                "form_data": form_data,
                "error": str(e),
                "admin": admin,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "Class/create.html",
            {
                **options,
                "form_data": form_data,
                "error": f"Lỗi khi tạo lớp học: {str(e)}",
                "admin": admin,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@class_router.get("/edit/{class_id}", response_class=HTMLResponse)
def edit_class_form(request: Request, class_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")

    options = _load_form_options(db)

    return render_template(
        request,
        "Class/edit.html",
        {
            **options,
            "cls": clazz,
            "admin": admin,
        },
    )


@class_router.post("/edit/{class_id}", response_class=HTMLResponse)
def edit_class(
    request: Request,
    class_id: str,
    class_code: str = Form(...),
    class_name: str = Form(...),
    class_type: str = Form("official"),
    academic_year_id: str = Form(""),
    major_id: str = Form(""),
    homeroom_teacher_id: str = Form(""),
    grade_level: int | None = Form(None),
    max_students: int = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    enrollment_start: str = Form(""),
    enrollment_end: str = Form(""),
    status_value: str = Form("planning", alias="status"),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")

    options = _load_form_options(db)

    form_data = {
        "id": class_id,
        "class_code": class_code,
        "class_name": class_name,
        "class_type": class_type,
        "academic_year_id": academic_year_id or None,
        "major_id": major_id or None,
        "homeroom_teacher_id": homeroom_teacher_id or None,
        "grade_level": grade_level,
        "max_students": max_students,
        "start_date": _parse_date(start_date) if start_date else None,
        "end_date": _parse_date(end_date) if end_date else None,
        "enrollment_start": _parse_date(enrollment_start) if enrollment_start else None,
        "enrollment_end": _parse_date(enrollment_end) if enrollment_end else None,
        "status": status_value,
    }

    try:
        update_class(db, class_id, form_data)

        message = quote("Cập nhật lớp học thành công.")
        return RedirectResponse(
            url=f"/admin/Class/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        return render_template(
            request,
            "Class/edit.html",
            {
                **options,
                "cls": form_data,
                "error": str(e),
                "admin": admin,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return render_template(
            request,
            "Class/edit.html",
            {
                **options,
                "cls": form_data,
                "error": f"Lỗi khi cập nhật lớp: {str(e)}",
                "admin": admin,
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@class_router.get("/delete/{class_id}", response_class=HTMLResponse)
def delete_class_form(request: Request, class_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")

    return render_template(
        request,
        "Class/delete.html",
        {
            "cls": clazz,
            "admin": admin,
        },
    )


@class_router.post("/delete/{class_id}")
def remove_class(class_id: str, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    del admin
    try:
        delete_class(db, class_id)
        message = quote("Xóa lớp học thành công.")
        return RedirectResponse(
            url=f"/admin/Class/manage?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/Class/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi xóa lớp: {str(e)}")
        return RedirectResponse(
            url=f"/admin/Class/manage?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@class_router.get("/students/{class_id}", response_class=HTMLResponse)
def manage_class_students(
    request: Request,
    class_id: str,
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học.")

    students = _get_students_in_class_view(db, class_id)
    available_students = _get_available_students_view(db, class_id)

    return render_template(
        request,
        "Class/students.html",
        {
            "cls": clazz,
            "students": students,
            "available_students": available_students,
            "success": success,
            "error": error,
            "admin": admin,
        },
    )


@class_router.post("/add-student")
def add_student_to_class_route(
    class_id: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        add_student_to_class(db, class_id, student_id)
        message = quote("Thêm sinh viên vào lớp thành công.")
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi thêm sinh viên vào lớp: {str(e)}")
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@class_router.post("/remove-student")
def remove_student_from_class_route(
    class_id: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        removed = remove_student_from_class(db, class_id, student_id)
        if not removed:
            raise ValueError("Không tìm thấy ghi danh của sinh viên trong lớp.")

        message = quote("Đã gỡ sinh viên khỏi lớp.")
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?success={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except ValueError as e:
        message = quote(str(e))
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        message = quote(f"Lỗi khi gỡ sinh viên khỏi lớp: {str(e)}")
        return RedirectResponse(
            url=f"/admin/Class/students/{class_id}?error={message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )