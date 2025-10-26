from fastapi import (
    APIRouter, Request, Depends, Form, HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

# ✅ Import models & services
from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
from app.database.connection import get_db
from app.services.teacher import assignment_service
from app.dependencies.auth import get_current_teacher

# ✅ Template dùng chung
from app.config.template_config import get_template_by_path


# ======================================================
# 🚀 Khởi tạo Router
# ======================================================
router = APIRouter(
    prefix="/teacher/assignments",
    tags=["Teacher - Assignments"]
)


# ======================================================
# 🧭 0️⃣ Route gốc → Redirect về danh sách
# ======================================================
@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    """Khi truy cập /teacher/assignments → tự động về /list"""
    return RedirectResponse("/teacher/assignments/list", status_code=303)


# ======================================================
# 📋 1️⃣ Danh sách bài tập
# ======================================================
@router.get("/list", response_class=HTMLResponse)
def list_assignments(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị danh sách bài tập của giáo viên"""
    try:
        teacher_id = current_teacher.id
        assignments = assignment_service.get_assignments_by_teacher(db, teacher_id)

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "assignments/list.html",
            {
                "request": request,
                "assignments": assignments,
                "now": datetime.now,
                "teacher_name": current_teacher.full_name,
            },
        )
    except Exception as e:
        print("❌ Lỗi khi tải danh sách bài tập:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tải danh sách bài tập.")


# ======================================================
# ➕ 2️⃣ Form tạo bài tập (GET)
# ======================================================
@router.get("/create", response_class=HTMLResponse)
def create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form tạo bài tập"""
    try:
        teacher_id = current_teacher.id
        courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()
        course_ids = [c.id for c in courses]
        modules = db.query(Module).filter(Module.course_id.in_(course_ids)).all()

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "assignments/create.html",
            {"request": request, "courses": courses, "modules": modules},
        )
    except Exception as e:
        print("❌ Lỗi khi tải form tạo bài tập:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tải form tạo bài tập.")


# ======================================================
# 💾 3️⃣ Xử lý tạo bài tập (POST)
# ======================================================
@router.post("/create", response_class=HTMLResponse)
def create_assignment(
    request: Request,
    course_id: str = Form(...),
    module_id: str = Form(None),
    title: str = Form(...),
    description: str = Form(""),
    due_date: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Tạo mới bài tập"""
    try:
        teacher_id = current_teacher.id

        # ✅ Kiểm tra khóa học hợp lệ
        course = db.query(Course).filter(
            Course.id == course_id, Course.teacher_id == teacher_id
        ).first()
        if not course:
            raise HTTPException(status_code=400, detail="Khóa học không hợp lệ.")

        # ✅ Kiểm tra module (nếu có)
        if module_id:
            module = db.query(Module).filter(Module.id == module_id).first()
            if not module:
                raise HTTPException(status_code=400, detail="Module không tồn tại.")

        # ✅ Gọi service tạo bài tập
        assignment_service.create_assignment(
            db=db,
            course_id=course_id,
            module_id=module_id,
            teacher_id=teacher_id,
            title=title,
            description=description,
            due_date=datetime.fromisoformat(due_date),
        )

        return RedirectResponse("/teacher/assignments/list", status_code=303)
    except Exception as e:
        print("❌ Lỗi khi tạo bài tập:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tạo bài tập.")


# ======================================================
# ✏️ 4️⃣ Sửa bài tập
# ======================================================
@router.get("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_form(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form sửa bài tập"""
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/edit.html",
        {
            "request": request,
            "assignment": assignment,
            "teacher_name": current_teacher.full_name,
        },
    )


@router.post("/edit/{assignment_id}", response_class=HTMLResponse)
def update_assignment(
    assignment_id: str,
    title: str = Form(...),
    description: str = Form(""),
    due_date: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Cập nhật thông tin bài tập"""
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    assignment.title = title
    assignment.description = description
    assignment.due_date = datetime.fromisoformat(due_date)
    assignment.updated_at = datetime.now()
    db.commit()

    return RedirectResponse("/teacher/assignments/list", status_code=303)


# ======================================================
# 🗑️ 5️⃣ Xóa bài tập
# ======================================================
@router.post("/delete/{assignment_id}")
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xóa bài tập"""
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.id == assignment_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    db.delete(assignment)
    db.commit()
    return RedirectResponse("/teacher/assignments/list", status_code=303)


# ======================================================
# 📄 6️⃣ Danh sách bài nộp
# ======================================================
@router.get("/submissions/{assignment_id}", response_class=HTMLResponse)
def view_submissions(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xem danh sách bài nộp"""
    try:
        submissions = assignment_service.get_submissions_by_assignment(db, assignment_id)
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            raise HTTPException(status_code=404, detail="Bài tập không tồn tại.")

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "assignments/submissions.html",
            {
                "request": request,
                "submissions": submissions,
                "assignment": assignment,
                "teacher_name": current_teacher.full_name,
            },
        )
    except Exception as e:
        print("❌ Lỗi khi tải danh sách bài nộp:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tải danh sách bài nộp.")


# ======================================================
# 🧮 7️⃣ Chấm điểm bài nộp
# ======================================================
@router.get("/grade/{submission_id}", response_class=HTMLResponse)
def grade_form(
    submission_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Hiển thị form chấm điểm"""
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    student = db.query(User).filter(User.id == submission.student_id).first()

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/grade.html",
        {"request": request, "submission": submission, "student": student},
    )


@router.post("/grade/{submission_id}")
def submit_grade(
    submission_id: str,
    grade: float = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher)
):
    """Xử lý chấm điểm"""
    try:
        updated = assignment_service.grade_submission(
            db=db,
            submission_id=submission_id,
            grade=grade,
            feedback=feedback,
            teacher_id=current_teacher.id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Bài nộp không tồn tại.")

        return RedirectResponse(
            f"/teacher/assignments/submissions/{updated.assignment_id}",
            status_code=303,
        )
    except Exception as e:
        print("❌ Lỗi khi chấm điểm:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể chấm điểm bài nộp.")
