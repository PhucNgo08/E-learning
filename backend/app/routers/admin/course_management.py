from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.course import Course
from app.models.major import Major
from app.models.user import User
from app.services import course_service
from app.utils.db_error_helper import (
    get_decimal_max_from_column,
    humanize_db_error,
    parse_money_vn,
)
from app.utils.user_query import filter_users_by_role


logger = logging.getLogger(__name__)
PRICE_MAX = get_decimal_max_from_column(Course, "price", Decimal("99999999.99"))

course_router = APIRouter(
    prefix="/admin/Course",
    tags=["Admin - Course Management"],
)


# ============================================================
# HELPERS
# ============================================================
def _require_admin(request: Request):
    if request.session.get("role") != "admin":
        return RedirectResponse("/auth/login", status_code=303)
    return None


def _consume_flash(request: Request) -> dict:
    return {
        "flash_success": request.session.pop("flash_success", None),
        "flash_error": request.session.pop("flash_error", None),
    }


def _blank_to_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _parse_int(value: str | None, label: str, errors: list[str], default=None):
    v = (value or "").strip()
    if v == "":
        return default
    try:
        return int(v)
    except Exception:
        errors.append(f"{label} phải là số nguyên.")
        return default


def _parse_date(value: str | None, label: str, errors: list[str]):
    v = (value or "").strip()
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        errors.append(f"{label} không đúng định dạng ngày YYYY-MM-DD.")
        return None


def _validate_choice(
    value: str | None,
    label: str,
    allowed: set[str],
    errors: list[str],
    default: str,
):
    v = (value or "").strip() or default
    if v not in allowed:
        errors.append(f"{label} không hợp lệ.")
        return default
    return v


def _validate_publish_requirements(
    *,
    status_str: str,
    teacher_id: str | None,
    academic_year_id: str | None,
    major_id: str | None,
    start_date_obj,
    end_date_obj,
    errors: list[str],
):
    if status_str != "published":
        return

    if not teacher_id:
        errors.append("Muốn xuất bản khóa học phải chọn giảng viên.")

    if not academic_year_id:
        errors.append("Muốn xuất bản khóa học phải chọn năm học.")

    if not major_id:
        errors.append("Muốn xuất bản khóa học phải chọn chuyên ngành.")

    if not start_date_obj:
        errors.append("Muốn xuất bản khóa học phải có ngày bắt đầu.")

    if not end_date_obj:
        errors.append("Muốn xuất bản khóa học phải có ngày kết thúc.")


def _base_form_context(request: Request, db: Session) -> dict:
    return {
        "request": request,
        "teachers": filter_users_by_role(db.query(User), "teacher").all(),
        "years": db.query(AcademicYear).all(),
        "majors": db.query(Major).all(),
        **_consume_flash(request),
    }


def _render_form(
    tpl,
    template_name: str,
    request: Request,
    db: Session,
    *,
    course: Course | None = None,
    form: dict | None = None,
    errors: list[str] | None = None,
    status_code: int = 200,
):
    context = _base_form_context(request, db)
    if course is not None:
        context["course"] = course
    if form is not None:
        context["form"] = form
    if errors is not None:
        context["errors"] = errors

    return tpl.TemplateResponse(template_name, context, status_code=status_code)


def _build_form_data(
    *,
    course_name: str,
    description: str,
    credit_hours: str,
    grade_level: str,
    semester: str,
    price: str,
    max_students: str,
    is_public: str,
    subject: str,
    teacher_id: str | None,
    academic_year_id: str | None,
    major_id: str | None,
    course_type: str,
    difficulty_level: str,
    enrollment_mode: str,
    prerequisites: str | None,
    allow_assignments: str,
    default_submission_type: str,
    start_date: str | None,
    end_date: str | None,
    status_str: str = "draft",
):
    return {
        "course_name": course_name,
        "description": description,
        "credit_hours": credit_hours,
        "grade_level": grade_level,
        "semester": semester,
        "price": price,
        "max_students": max_students,
        "is_public": is_public,
        "subject": subject,
        "teacher_id": teacher_id,
        "academic_year_id": academic_year_id,
        "major_id": major_id,
        "course_type": course_type,
        "difficulty_level": difficulty_level,
        "enrollment_mode": enrollment_mode,
        "prerequisites": prerequisites,
        "allow_assignments": allow_assignments,
        "default_submission_type": default_submission_type,
        "start_date": start_date,
        "end_date": end_date,
        "status_str": status_str,
    }


# =====================================================================================
# 1) Danh sách khóa học
# =====================================================================================
@course_router.get("/manage", response_class=HTMLResponse)
async def manage_courses(
    request: Request,
    db: Session = Depends(get_db),
    q: str | None = Query(None),
    status: str | None = Query(None),
    teacher_id: str | None = Query(None),
    major_id: str | None = Query(None),
    year_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    query = (
        db.query(Course)
        .join(User, Course.teacher_id == User.id, isouter=True)
        .filter(Course.deleted_at.is_(None))
    )

    if q:
        s = f"%{q.strip()}%"
        query = query.filter(
            Course.course_name.ilike(s) |
            Course.course_code.ilike(s)
        )

    if status:
        query = query.filter(Course.status == status)

    if teacher_id:
        query = query.filter(Course.teacher_id == teacher_id)

    if major_id:
        query = query.filter(Course.major_id == major_id)

    if year_id:
        query = query.filter(Course.academic_year_id == year_id)

    total = query.with_entities(func.count(Course.id)).scalar() or 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    courses = (
        query.order_by(Course.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return tpl.TemplateResponse(
        "Course/manage.html",
        {
            "request": request,
            "courses": courses,
            "teachers": filter_users_by_role(db.query(User), "teacher").all(),
            "majors": db.query(Major).all(),
            "years": db.query(AcademicYear).all(),
            "total": total,
            "current_page": page,
            "total_pages": total_pages,
            "q": q,
            "status": status,
            "teacher_id": teacher_id,
            "major_id": major_id,
            "year_id": year_id,
            **_consume_flash(request),
        },
    )


# =====================================================================================
# 2) GET: Trang tạo khóa học
# =====================================================================================
@course_router.get("/create", response_class=HTMLResponse)
async def create_page(request: Request, db: Session = Depends(get_db)):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)
    return _render_form(tpl, "Course/create.html", request, db)


# =====================================================================================
# 3) POST: Tạo khóa học
# =====================================================================================
@course_router.post("/create", response_class=HTMLResponse)
async def create_course(
    request: Request,
    db: Session = Depends(get_db),

    course_name: str = Form(""),
    description: str = Form(""),

    credit_hours: str = Form("3"),
    grade_level: str = Form(""),
    semester: str = Form(""),
    price: str = Form("0"),
    max_students: str = Form("100"),
    is_public: str = Form("0"),

    subject: str = Form("Other"),
    teacher_id: str | None = Form(None),
    academic_year_id: str | None = Form(None),
    major_id: str | None = Form(None),

    course_type: str = Form("online"),
    difficulty_level: str = Form("beginner"),
    enrollment_mode: str = Form("auto"),

    prerequisites: str | None = Form(None),
    allow_assignments: str = Form("1"),
    default_submission_type: str = Form("individual"),

    start_date: str | None = Form(None),
    end_date: str | None = Form(None),

    status_str: str = Form("draft"),
    thumbnail: UploadFile | None = File(None),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    teacher_id = _blank_to_none(teacher_id)
    academic_year_id = _blank_to_none(academic_year_id)
    major_id = _blank_to_none(major_id)
    prerequisites = _blank_to_none(prerequisites)

    form_data = _build_form_data(
        course_name=course_name,
        description=description,
        credit_hours=credit_hours,
        grade_level=grade_level,
        semester=semester,
        price=price,
        max_students=max_students,
        is_public=is_public,
        subject=subject,
        teacher_id=teacher_id,
        academic_year_id=academic_year_id,
        major_id=major_id,
        course_type=course_type,
        difficulty_level=difficulty_level,
        enrollment_mode=enrollment_mode,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments,
        default_submission_type=default_submission_type,
        start_date=start_date,
        end_date=end_date,
        status_str=status_str,
    )

    errors: list[str] = []

    course_name = (course_name or "").strip()
    subject = (subject or "").strip() or "Other"

    credit_hours_i = _parse_int(credit_hours, "Số tín chỉ", errors, 3)
    grade_level_i = _parse_int(grade_level, "Khối/Lớp", errors, None)
    semester_i = _parse_int(semester, "Học kỳ", errors, None)
    max_students_i = _parse_int(max_students, "Số lượng tối đa", errors, 100)
    is_public_i = _parse_int(is_public, "Công khai", errors, 0)
    allow_assignments_i = _parse_int(allow_assignments, "Cho phép bài tập", errors, 1)

    course_type = _validate_choice(
        course_type,
        "Loại khóa học",
        {"mandatory", "elective", "workshop", "online", "hybrid"},
        errors,
        "online",
    )

    difficulty_level = _validate_choice(
        difficulty_level,
        "Độ khó",
        {"beginner", "intermediate", "advanced"},
        errors,
        "beginner",
    )

    enrollment_mode = _validate_choice(
        enrollment_mode,
        "Chế độ đăng ký",
        {"auto", "approval", "invite_only"},
        errors,
        "auto",
    )

    default_submission_type = _validate_choice(
        default_submission_type,
        "Hình thức nộp bài",
        {"individual", "group"},
        errors,
        "individual",
    )

    status_str = _validate_choice(
        status_str,
        "Trạng thái",
        {"draft", "published", "archived"},
        errors,
        "draft",
    )

    try:
        price_d = parse_money_vn(price)
    except (InvalidOperation, ValueError):
        price_d = Decimal("0")
        errors.append("Giá khóa học phải là số.")

    if price_d < 0:
        errors.append("Giá khóa học không được âm.")

    if price_d > PRICE_MAX:
        errors.append(f"Giá khóa học tối đa {PRICE_MAX:,.2f} VNĐ.")

    start_date_obj = _parse_date(start_date, "Ngày bắt đầu", errors)
    end_date_obj = _parse_date(end_date, "Ngày kết thúc", errors)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        errors.append("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")

    if not course_name:
        errors.append("Tên khóa học không được để trống.")

    if credit_hours_i is not None and credit_hours_i <= 0:
        errors.append("Số tín chỉ phải lớn hơn 0.")

    if max_students_i is not None and max_students_i <= 0:
        errors.append("Số lượng tối đa phải lớn hơn 0.")

    _validate_publish_requirements(
        status_str=status_str,
        teacher_id=teacher_id,
        academic_year_id=academic_year_id,
        major_id=major_id,
        start_date_obj=start_date_obj,
        end_date_obj=end_date_obj,
        errors=errors,
    )

    if errors:
        return _render_form(
            tpl,
            "Course/create.html",
            request,
            db,
            form=form_data,
            errors=errors,
            status_code=400,
        )

    try:
        new_course = await course_service.create_course(
            db=db,
            user_id=request.session.get("user_id"),
            course_name=course_name,
            description=description,
            credit_hours=credit_hours_i,
            subject=subject,
            grade_level=grade_level_i,
            thumbnail=thumbnail,
            role="admin",
            teacher_id=teacher_id,
            major_id=major_id,
            academic_year_id=academic_year_id,
            semester=semester_i,
            price=float(price_d),
            difficulty_level=difficulty_level,
            enrollment_mode=enrollment_mode,
            max_students=max_students_i,
            is_public=is_public_i,
            prerequisites=prerequisites,
            allow_assignments=allow_assignments_i,
            default_submission_type=default_submission_type,
            status=status_str,
        )

        new_course.course_type = course_type
        new_course.start_date = start_date_obj
        new_course.end_date = end_date_obj
        new_course.status = status_str
        db.commit()

    except (DataError, IntegrityError) as e:
        db.rollback()
        logger.exception("DB error when creating course")
        return _render_form(
            tpl,
            "Course/create.html",
            request,
            db,
            form=form_data,
            errors=[humanize_db_error(e, price_max=PRICE_MAX)],
            status_code=400,
        )

    except Exception:
        db.rollback()
        logger.exception("Unexpected error when creating course")
        return _render_form(
            tpl,
            "Course/create.html",
            request,
            db,
            form=form_data,
            errors=["Có lỗi hệ thống khi tạo khóa học. Vui lòng thử lại."],
            status_code=500,
        )

    request.session["flash_success"] = "✅ Tạo khóa học thành công!"
    return RedirectResponse("/admin/Course/manage", status_code=303)


# =====================================================================================
# 4) GET: Trang edit khóa học
# =====================================================================================
@course_router.get("/edit/{course_id}", response_class=HTMLResponse)
async def page_edit(course_id: str, request: Request, db: Session = Depends(get_db)):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    course = course_service.get_course_owned(
        db,
        request.session.get("user_id"),
        course_id,
        role="admin",
    )

    if not course or course.deleted_at is not None:
        request.session["flash_error"] = "Không tìm thấy khóa học."
        return RedirectResponse("/admin/Course/manage", status_code=303)

    return _render_form(
        tpl,
        "Course/edit.html",
        request,
        db,
        course=course,
    )


# =====================================================================================
# 5) POST: Cập nhật khóa học
# =====================================================================================
@course_router.post("/edit/{course_id}", response_class=HTMLResponse)
async def update_course_action(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),

    course_name: str = Form(""),
    description: str = Form(""),

    credit_hours: str = Form("3"),
    grade_level: str = Form(""),
    semester: str = Form(""),
    price: str = Form("0"),
    max_students: str = Form("100"),
    is_public: str = Form("0"),
    allow_assignments: str = Form("1"),

    status_str: str = Form("draft"),
    subject: str = Form("Other"),

    teacher_id: str | None = Form(None),
    academic_year_id: str | None = Form(None),
    major_id: str | None = Form(None),

    course_type: str = Form("online"),
    difficulty_level: str = Form("beginner"),
    enrollment_mode: str = Form("auto"),

    prerequisites: str | None = Form(None),
    default_submission_type: str = Form("individual"),

    start_date: str | None = Form(None),
    end_date: str | None = Form(None),

    thumbnail: UploadFile | None = File(None),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    course = course_service.get_course_owned(
        db,
        request.session.get("user_id"),
        course_id,
        role="admin",
    )

    if not course or course.deleted_at is not None:
        request.session["flash_error"] = "Không tìm thấy khóa học."
        return RedirectResponse("/admin/Course/manage", status_code=303)

    teacher_id = _blank_to_none(teacher_id)
    academic_year_id = _blank_to_none(academic_year_id)
    major_id = _blank_to_none(major_id)
    prerequisites = _blank_to_none(prerequisites)

    form_data = _build_form_data(
        course_name=course_name,
        description=description,
        credit_hours=credit_hours,
        grade_level=grade_level,
        semester=semester,
        price=price,
        max_students=max_students,
        is_public=is_public,
        subject=subject,
        teacher_id=teacher_id,
        academic_year_id=academic_year_id,
        major_id=major_id,
        course_type=course_type,
        difficulty_level=difficulty_level,
        enrollment_mode=enrollment_mode,
        prerequisites=prerequisites,
        allow_assignments=allow_assignments,
        default_submission_type=default_submission_type,
        start_date=start_date,
        end_date=end_date,
        status_str=status_str,
    )

    errors: list[str] = []

    course_name = (course_name or "").strip()
    subject = (subject or "").strip() or "Other"

    credit_hours_i = _parse_int(credit_hours, "Số tín chỉ", errors, 3)
    grade_level_i = _parse_int(grade_level, "Khối/Lớp", errors, None)
    semester_i = _parse_int(semester, "Học kỳ", errors, None)
    max_students_i = _parse_int(max_students, "Số lượng tối đa", errors, 100)
    is_public_i = _parse_int(is_public, "Công khai", errors, 0)
    allow_assignments_i = _parse_int(allow_assignments, "Cho phép bài tập", errors, 1)

    course_type = _validate_choice(
        course_type,
        "Loại khóa học",
        {"mandatory", "elective", "workshop", "online", "hybrid"},
        errors,
        "online",
    )

    difficulty_level = _validate_choice(
        difficulty_level,
        "Độ khó",
        {"beginner", "intermediate", "advanced"},
        errors,
        "beginner",
    )

    enrollment_mode = _validate_choice(
        enrollment_mode,
        "Chế độ đăng ký",
        {"auto", "approval", "invite_only"},
        errors,
        "auto",
    )

    default_submission_type = _validate_choice(
        default_submission_type,
        "Hình thức nộp bài",
        {"individual", "group"},
        errors,
        "individual",
    )

    status_str = _validate_choice(
        status_str,
        "Trạng thái",
        {"draft", "published", "archived"},
        errors,
        "draft",
    )

    try:
        price_d = parse_money_vn(price)
    except (InvalidOperation, ValueError):
        price_d = Decimal("0")
        errors.append("Giá khóa học phải là số.")

    if price_d < 0:
        errors.append("Giá khóa học không được âm.")

    if price_d > PRICE_MAX:
        errors.append(f"Giá khóa học tối đa {PRICE_MAX:,.2f} VNĐ.")

    start_date_obj = _parse_date(start_date, "Ngày bắt đầu", errors)
    end_date_obj = _parse_date(end_date, "Ngày kết thúc", errors)

    if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
        errors.append("Ngày kết thúc không được nhỏ hơn ngày bắt đầu.")

    if not course_name:
        errors.append("Tên khóa học không được để trống.")

    if credit_hours_i is not None and credit_hours_i <= 0:
        errors.append("Số tín chỉ phải lớn hơn 0.")

    if max_students_i is not None and max_students_i <= 0:
        errors.append("Số lượng tối đa phải lớn hơn 0.")

    _validate_publish_requirements(
        status_str=status_str,
        teacher_id=teacher_id,
        academic_year_id=academic_year_id,
        major_id=major_id,
        start_date_obj=start_date_obj,
        end_date_obj=end_date_obj,
        errors=errors,
    )

    if errors:
        return _render_form(
            tpl,
            "Course/edit.html",
            request,
            db,
            course=course,
            form=form_data,
            errors=errors,
            status_code=400,
        )

    try:
        updated = await course_service.update_course(
            db=db,
            user_id=request.session.get("user_id"),
            course_id=course_id,
            course_name=course_name,
            description=description,
            credit_hours=credit_hours_i,
            status_str=status_str,
            subject=subject,
            grade_level=grade_level_i,
            thumbnail=thumbnail,
            role="admin",
            teacher_id=teacher_id,
            major_id=major_id,
            academic_year_id=academic_year_id,
            price=float(price_d),
            difficulty_level=difficulty_level,
            enrollment_mode=enrollment_mode,
            max_students=max_students_i,
            semester=semester_i,
            is_public=is_public_i,
            prerequisites=prerequisites,
            allow_assignments=allow_assignments_i,
            default_submission_type=default_submission_type,
        )

        target_course = updated if hasattr(updated, "id") else course
        target_course.course_type = course_type
        target_course.start_date = start_date_obj
        target_course.end_date = end_date_obj
        target_course.status = status_str
        db.commit()

    except (DataError, IntegrityError) as e:
        db.rollback()
        logger.exception("DB error when updating course")
        return _render_form(
            tpl,
            "Course/edit.html",
            request,
            db,
            course=course,
            form=form_data,
            errors=[humanize_db_error(e, price_max=PRICE_MAX)],
            status_code=400,
        )

    except Exception:
        db.rollback()
        logger.exception("Unexpected error when updating course")
        return _render_form(
            tpl,
            "Course/edit.html",
            request,
            db,
            course=course,
            form=form_data,
            errors=["Có lỗi hệ thống khi cập nhật. Vui lòng thử lại."],
            status_code=500,
        )

    request.session["flash_success"] = "✅ Cập nhật khóa học thành công!"
    return RedirectResponse("/admin/Course/manage", status_code=303)


# =====================================================================================
# 6) Xóa khóa học
# =====================================================================================
@course_router.post("/delete/{course_id}")
async def delete_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    try:
        ok = course_service.delete_course(
            db,
            request.session.get("user_id"),
            course_id,
            role="admin",
        )

        if not ok:
            request.session["flash_error"] = "Không thể xóa khóa học."
            return RedirectResponse("/admin/Course/manage", status_code=303)

        request.session["flash_success"] = "✅ Xóa khóa học thành công!"
        return RedirectResponse("/admin/Course/manage", status_code=303)

    except Exception:
        logger.exception("Unexpected error when deleting course")
        request.session["flash_error"] = "Có lỗi hệ thống khi xóa khóa học."
        return RedirectResponse("/admin/Course/manage", status_code=303)


@course_router.get("/delete/{course_id}", response_class=HTMLResponse)
async def delete_course_confirm(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.deleted_at.is_(None))
        .first()
    )

    if not course:
        request.session["flash_error"] = "Không tìm thấy khóa học."
        return RedirectResponse("/admin/Course/manage", status_code=303)

    return tpl.TemplateResponse(
        "Course/delete.html",
        {
            "request": request,
            "course": course,
            **_consume_flash(request),
        },
    )


# =====================================================================================
# 7) Chi tiết khóa học
# =====================================================================================
@course_router.get("/detail/{course_id}", response_class=HTMLResponse)
async def course_detail(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.deleted_at.is_(None))
        .first()
    )

    if not course:
        request.session["flash_error"] = "Không tìm thấy khóa học."
        return RedirectResponse("/admin/Course/manage", status_code=303)

    teacher = None
    if course.teacher_id:
        teacher = db.query(User).filter(User.id == course.teacher_id).first()

    return tpl.TemplateResponse(
        "Course/detail.html",
        {
            "request": request,
            "course": course,
            "teacher": teacher,
            "now": datetime.now(),
            **_consume_flash(request),
        },
    )


# =====================================================================================
# 8) Tổng quan khóa học
# =====================================================================================
@course_router.get("/overview", response_class=HTMLResponse)
async def course_overview(request: Request, db: Session = Depends(get_db)):
    auth_redirect = _require_admin(request)
    if auth_redirect:
        return auth_redirect

    tpl = get_template_by_path(request.url.path)

    latest_course = (
        db.query(Course)
        .filter(Course.deleted_at.is_(None))
        .order_by(Course.created_at.desc())
        .first()
    )

    return tpl.TemplateResponse(
        "Course/overview.html",
        {
            "request": request,
            "total_courses": (
                db.query(func.count(Course.id))
                .filter(Course.deleted_at.is_(None))
                .scalar()
                or 0
            ),
            "total_teachers": filter_users_by_role(db.query(User), "teacher").count(),
            "total_students": filter_users_by_role(db.query(User), "student").count(),
            "course": latest_course,
            **_consume_flash(request),
        },
    )