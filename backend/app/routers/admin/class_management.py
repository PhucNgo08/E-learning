# ============================================================
# 🏫 class_management.py — Quản lý Lớp học (Admin)
# ============================================================
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

# ==============================
# 📦 Import DB & Models
# ==============================
from app.database.connection import get_db
from app.models.academic_year import AcademicYear
from app.models.major import Major
from app.models.user import User
from app.models.enrollment import Enrollment

# 📦 Import service
from app.services.admin.class_management_service import (
    create_class,
    get_all_classes,
    update_class,
    delete_class,
    get_class_by_id,
)

# Template config
from app.config.template_config import get_template_by_path


# ============================================================
# ⚙️ Router
# ============================================================
class_router = APIRouter(
    prefix="/admin/Class",
    tags=["Admin - Class Management"]
)


# ============================================================
# 📋 1️⃣ Danh sách lớp học
# ============================================================
@class_router.get("/manage", response_class=HTMLResponse)
def manage_classes(request: Request, db: Session = Depends(get_db)):
    try:
        tpl = get_template_by_path(request.url.path)
        classes = get_all_classes(db)
        return tpl.TemplateResponse(
            "Class/manage.html",
            {"request": request, "classes": classes},
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi tải danh sách lớp: {str(e)}")


# ============================================================
# ➕ 2️⃣ Form tạo lớp
# ============================================================
@class_router.get("/create", response_class=HTMLResponse)
def create_class_form(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()

    return tpl.TemplateResponse(
        "Class/create.html",
        {
            "request": request,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers,
        },
    )


# ============================================================
# 💾 3️⃣ Xử lý tạo lớp học — ĐÃ SỬA KHỚP THAM SỐ
# ============================================================
@class_router.post("/create")
def add_class(
    class_code: str = Form(...),
    class_name: str = Form(...),
    class_type: str = Form("official"),

    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    homeroom_teacher_id: str = Form(None),

    grade_level: int = Form(None),
    max_students: int = Form(50),

    start_date: str = Form(None),
    end_date: str = Form(None),
    enrollment_start: str = Form(None),
    enrollment_end: str = Form(None),

    db: Session = Depends(get_db),
):
    try:
        # Convert date
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        enroll_start_dt = datetime.strptime(enrollment_start, "%Y-%m-%d") if enrollment_start else None
        enroll_end_dt = datetime.strptime(enrollment_end, "%Y-%m-%d") if enrollment_end else None

        # 🚀 Gọi service đúng chuẩn
        create_class(
            db,
            class_code,
            class_name,
            class_type,
            academic_year_id,
            major_id,
            grade_level,
            max_students,
            homeroom_teacher_id,
            start_dt,
            end_dt,
            enroll_start_dt,
            enroll_end_dt,
        )

        return RedirectResponse("/admin/Class/manage", status_code=303)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi tạo lớp học: {str(e)}")


# ============================================================
# ✏️ 4️⃣ Form sửa lớp
# ============================================================
@class_router.get("/edit/{class_id}", response_class=HTMLResponse)
def edit_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(404, "Không tìm thấy lớp học.")

    majors = db.query(Major).all()
    academic_years = db.query(AcademicYear).all()
    teachers = db.query(User).filter(User.role == "teacher").all()

    return tpl.TemplateResponse(
        "Class/edit.html",
        {
            "request": request,
            "cls": clazz,
            "majors": majors,
            "academic_years": academic_years,
            "teachers": teachers,
        },
    )


# ============================================================
# 🔄 5️⃣ Xử lý cập nhật lớp — KHỚP THAM SỐ
# ============================================================
@class_router.post("/edit/{class_id}")
def edit_class(
    class_id: str,

    class_code: str = Form(...),
    class_name: str = Form(...),
    class_type: str = Form("official"),

    academic_year_id: str = Form(None),
    major_id: str = Form(None),
    homeroom_teacher_id: str = Form(None),

    grade_level: int = Form(None),
    max_students: int = Form(...),

    start_date: str = Form(None),
    end_date: str = Form(None),
    enrollment_start: str = Form(None),
    enrollment_end: str = Form(None),

    db: Session = Depends(get_db),
):
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        enroll_start_dt = datetime.strptime(enrollment_start, "%Y-%m-%d") if enrollment_start else None
        enroll_end_dt = datetime.strptime(enrollment_end, "%Y-%m-%d") if enrollment_end else None

        update_class(
            db,
            class_id,
            {
                "class_code": class_code,
                "class_name": class_name,
                "class_type": class_type,
                "academic_year_id": academic_year_id,
                "major_id": major_id,
                "homeroom_teacher_id": homeroom_teacher_id,
                "grade_level": grade_level,
                "max_students": max_students,
                "start_date": start_dt,
                "end_date": end_dt,
                "enrollment_start": enroll_start_dt,
                "enrollment_end": enroll_end_dt,
            }
        )

        return RedirectResponse("/admin/Class/manage", status_code=303)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi cập nhật lớp: {str(e)}")


# ============================================================
# ❌ 6️⃣ Xác nhận xóa lớp
# ============================================================
@class_router.get("/delete/{class_id}", response_class=HTMLResponse)
def delete_class_form(request: Request, class_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)
    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(404, "Không tìm thấy lớp học.")

    return tpl.TemplateResponse(
        "Class/delete.html",
        {"request": request, "cls": clazz},
    )


# ============================================================
# 🗑️ 7️⃣ Xử lý xóa lớp
# ============================================================
@class_router.post("/delete/{class_id}")
def remove_class(class_id: str, db: Session = Depends(get_db)):
    try:
        delete_class(db, class_id)
        return RedirectResponse("/admin/Class/manage", status_code=303)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi xóa lớp: {str(e)}")


# ============================================================
# 👨‍🎓 8️⃣ DANH SÁCH SINH VIÊN TRONG LỚP
# ============================================================
@class_router.get("/students/{class_id}", response_class=HTMLResponse)
def manage_class_students(request: Request, class_id: str, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)

    clazz = get_class_by_id(db, class_id)
    if not clazz:
        raise HTTPException(404, "Không tìm thấy lớp học.")

    # Đã enrolled
    students = (
        db.query(User)
        .join(Enrollment, Enrollment.user_id == User.id)
        .filter(Enrollment.class_id == class_id)
        .filter(Enrollment.enrollment_status.in_(["approved", "active"]))
        .all()
    )

    # Học sinh có thể thêm
    available = (
        db.query(User)
        .filter(User.role == "student")
        .filter(~User.id.in_(
            db.query(Enrollment.user_id).filter(Enrollment.class_id == class_id)
        ))
        .all()
    )

    return tpl.TemplateResponse(
        "Class/students.html",
        {
            "request": request,
            "cls": clazz,
            "students": students,
            "available_students": available,
        },
    )


# ============================================================
# ➕ 9️⃣ GÁN SINH VIÊN VÀO LỚP
# ============================================================
@class_router.post("/add-student")
def add_student_to_class_route(
    class_id: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        from app.services.admin.class_management_service import add_student_to_class

        add_student_to_class(db, class_id, student_id)
        return RedirectResponse(f"/admin/Class/students/{class_id}", status_code=303)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi thêm sinh viên vào lớp: {str(e)}")


# ============================================================
# ❌ 🔟 XOÁ SINH VIÊN KHỎI LỚP
# ============================================================
@class_router.post("/remove-student")
def remove_student_from_class_route(
    class_id: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        from app.services.admin.class_management_service import remove_student_from_class

        remove_student_from_class(db, class_id, student_id)
        return RedirectResponse(f"/admin/Class/students/{class_id}", status_code=303)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Lỗi khi gỡ sinh viên khỏi lớp: {str(e)}")
