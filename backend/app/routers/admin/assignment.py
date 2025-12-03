from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
import traceback

from app.models.user import User
from app.models.course import Course
from app.models.module import Module
from app.models.assignment_submission import AssignmentSubmission
from app.database.connection import get_db

# ===== Service CHUẨN =====
from app.services.admin.assignment_service import (
    get_all,
    get_by_id,
    create_assignment,
    update_assignment,
    delete_assignment,
    get_global_assignment_report,
    get_teacher_assignment_stats,
    get_student_assignment_summary,
    get_assignment_analytics,
    export_assignment_scores_to_excel,
    grade_submission,         # <-- ✔ THÊM
)

# ==== Template ====
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/admin/assignment",
    tags=["Admin - Assignment Management"]
)


# =========================================================
# 📋 1️⃣ Danh sách bài tập
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def assignment_list(request: Request, db: Session = Depends(get_db)):
    try:
        tpl = get_template_by_path(request.url.path)

        assignments = get_all(db)
        stats = get_global_assignment_report(db)

        return tpl.TemplateResponse(
            "assignment/list.html",
            {
                "request": request,
                "assignments": assignments,
                "stats": stats,
                "current_year": datetime.now().year
            }
        )
    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📤 1.1 Danh sách bài nộp của một assignment
# =========================================================
@router.get("/submissions/{assignment_id}", response_class=HTMLResponse)
def list_submissions(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    try:
        tpl = get_template_by_path(request.url.path)

        submissions = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == assignment_id)
            .all()
        )

        assignment = get_by_id(db, assignment_id)

        return tpl.TemplateResponse(
            "assignment/list_submissions.html",
            {
                "request": request,
                "submissions": submissions,
                "assignment": assignment,
                "current_year": datetime.now().year
            }
        )
    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📝 1.2 Form chấm bài
# =========================================================
@router.get("/grade/{submission_id}", response_class=HTMLResponse)
def grade_form(request: Request, submission_id: str, db: Session = Depends(get_db)):
    try:
        tpl = get_template_by_path(request.url.path)

        submission = (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.id == submission_id)
            .first()
        )

        if not submission:
            raise HTTPException(404, "Không tìm thấy bài nộp.")

        return tpl.TemplateResponse(
            "assignment/grade.html",
            {
                "request": request,
                "submission": submission,
                "current_year": datetime.now().year
            }
        )
    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📝 1.3 POST chấm bài
# =========================================================
@router.post("/grade/{submission_id}")
def grade_submit(
    submission_id: str,
    grade: float = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        # Tạm thời: Admin/Teacher ID lấy từ cứng
        # Nếu bạn có system auth → đổi thành: request.state.user.id
        teacher_id = "ADMIN-MANUAL-ID"

        grade_submission(
            db=db,
            submission_id=submission_id,
            grade=grade,
            feedback=feedback,
            teacher_id=teacher_id
        )

        # Redirect về danh sách bài nộp
        sub = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.id == submission_id
        ).first()

        return RedirectResponse(
            f"/admin/assignment/submissions/{sub.assignment_id}",
            status_code=303
        )

    except HTTPException as e:
        return HTMLResponse(f"<h3 style='color:red;'>{e.detail}</h3>", status_code=400)

    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# ➕ 2️⃣ Form tạo bài tập
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_assignment_form(request: Request, db: Session = Depends(get_db)):
    tpl = get_template_by_path(request.url.path)

    teachers = db.query(User).filter(User.role == "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).all()

    return tpl.TemplateResponse(
        "assignment/create.html",
        {
            "request": request,
            "teachers": teachers,
            "courses": courses,
            "modules": modules,
            "current_year": datetime.now().year
        }
    )


# =========================================================
# ➕ POST tạo bài tập
# =========================================================
@router.post("/create")
def create_assignment_route(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(...),
    teacher_id: str = Form(None),
    module_id: str = Form(None),
    due_date: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        parsed_due_date = datetime.fromisoformat(due_date) if due_date else None

        create_assignment(
            db,
            title=title,
            description=description,
            course_id=course_id,
            due_date=parsed_due_date,
            teacher_id=teacher_id,
            module_id=module_id
        )

        return RedirectResponse(url="/admin/assignment/list", status_code=303)

    except HTTPException as e:
        db.rollback()
        return HTMLResponse(
            f"<h3 style='color:red;'>❌ {e.detail}</h3>",
            status_code=400
        )

    except Exception:
        db.rollback()
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# ✏️ 3️⃣ Sửa bài tập
# =========================================================
@router.get("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_form(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    tpl = get_template_by_path(request.url.path)

    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập.")

    teachers = db.query(User).filter(User.role == "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).filter(Module.course_id == assignment.course_id).all()

    return tpl.TemplateResponse(
        "assignment/edit.html",
        {
            "request": request,
            "assignment": assignment,
            "teachers": teachers,
            "courses": courses,
            "modules": modules,
            "current_year": datetime.now().year
        }
    )


@router.post("/edit/{assignment_id}")
def edit_assignment_route(
    assignment_id: str,
    title: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        update_assignment(db, assignment_id, title, description)

        return RedirectResponse(url="/admin/assignment/list", status_code=303)

    except Exception:
        db.rollback()
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 🗑️ 4️⃣ Xóa bài tập
# =========================================================
@router.get("/delete/{assignment_id}", response_class=HTMLResponse)
def delete_confirm(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    tpl = get_template_by_path(request.url.path)

    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(404, "Không tìm thấy bài tập.")

    return tpl.TemplateResponse(
        "assignment/delete.html",
        {
            "request": request,
            "assignment": assignment,
            "current_year": datetime.now().year
        }
    )


@router.post("/delete/{assignment_id}")
def delete_assignment_route(
    assignment_id: str,
    db: Session = Depends(get_db)
):
    try:
        delete_assignment(db, assignment_id)

        return RedirectResponse("/admin/assignment/list", status_code=303)

    except Exception:
        db.rollback()
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📊 5️⃣ Thống kê theo khóa học
# =========================================================
@router.get("/manage/{course_id}", response_class=HTMLResponse)
def manage_assignments(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db)
):
    try:
        tpl = get_template_by_path(request.url.path)
        stats = get_assignment_analytics(db, course_id)

        course = db.query(Course).filter(Course.id == course_id).first()

        return tpl.TemplateResponse(
            "assignment/manage.html",
            {
                "request": request,
                "stats": stats,
                "course": course
            }
        )

    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📈 6️⃣ Dashboard thống kê tổng hợp
# =========================================================
@router.get("/stats", response_class=HTMLResponse)
def assignment_stats_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        tpl = get_template_by_path(request.url.path)

        global_stats = get_global_assignment_report(db)

        teacher_stats = [
            {
                "teacher_name": t.full_name,
                "data": get_teacher_assignment_stats(db, t.id)
            }
            for t in db.query(User).filter(User.role == "teacher").all()
        ]

        student_stats = [
            {
                "student_name": s.full_name,
                "data": get_student_assignment_summary(db, s.id)
            }
            for s in db.query(User).filter(User.role == "student").limit(5).all()
        ]

        return tpl.TemplateResponse(
            "assignment/stats.html",
            {
                "request": request,
                "global_stats": global_stats,
                "teacher_stats": teacher_stats,
                "student_stats": student_stats,
                "current_year": datetime.now().year
            }
        )

    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)



# =========================================================
# 📤 7️⃣ Xuất Excel
# =========================================================
@router.get("/export_excel/{assignment_id}")
def export_assignment_excel(assignment_id: str, db: Session = Depends(get_db)):
    try:
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        file_path = export_dir / f"assignment_{assignment_id}.xlsx"

        export_assignment_scores_to_excel(db, assignment_id, str(file_path))

        return FileResponse(
            str(file_path),
            filename=file_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception:
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
