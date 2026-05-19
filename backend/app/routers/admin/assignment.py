from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config.template_config import get_template_by_path
from app.database.connection import get_db
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
from app.services.admin.assignment_service import (
    create_assignment,
    delete_assignment,
    export_assignment_scores_to_excel,
    get_all,
    get_assignment_analytics,
    get_by_id,
    get_global_assignment_report,
    get_student_assignment_summary,
    get_teacher_assignment_stats,
    grade_submission,
    update_assignment,
)
from app.utils.user_query import filter_users_by_role

router = APIRouter(
    prefix="/admin/assignment",
    tags=["Admin - Assignment Management"]
)

BACKEND_DIR = Path(__file__).resolve().parents[3]


def _is_remote_url(value: str) -> bool:
    lower = (value or "").lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _resolve_admin_download_path(file_url: str) -> Path | None:
    raw = str(file_url or "").strip()
    if not raw:
        return None

    candidate = Path(raw)
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        clean = raw.lstrip("/\\")
        candidates.extend([
            (BACKEND_DIR / clean),
            (BACKEND_DIR / "app" / clean),
        ])

    for path in candidates:
        resolved = path.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved

    return None


def render_template(request: Request, template_name: str, context: dict, status_code: int = 200):
    tpl = get_template_by_path(request.url.path)
    base_context = {
        "request": request,
        "current_year": datetime.now().year,
    }
    base_context.update(context)
    return tpl.TemplateResponse(template_name, base_context, status_code=status_code)


def _display_name(user):
    if not user:
        return "Không rõ"
    if getattr(user, "full_name", None):
        return user.full_name
    profile = getattr(user, "user_profile", None)
    if profile and getattr(profile, "full_name", None):
        return profile.full_name
    return getattr(user, "username", None) or getattr(user, "email", None) or "Không rõ"


# =========================================================
# 1) Danh sách bài tập
# =========================================================
@router.get("/list", response_class=HTMLResponse)
def assignment_list(
    request: Request,
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    assignments = get_all(db)
    stats = get_global_assignment_report(db)

    return render_template(
        request,
        "assignment/list.html",
        {
            "assignments": assignments,
            "stats": stats,
            "success": success,
            "error": error,
        }
    )


# =========================================================
# 1.1) Danh sách bài nộp của một assignment
# =========================================================
@router.get("/submissions/{assignment_id}", response_class=HTMLResponse)
def list_submissions(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submission_time.desc())
        .all()
    )

    return render_template(
        request,
        "assignment/list_submissions.html",
        {
            "submissions": submissions,
            "assignment": assignment,
        }
    )


# =========================================================
# 1.2) Form chấm bài
# =========================================================
@router.get("/grade/{submission_id}", response_class=HTMLResponse)
def grade_form(request: Request, submission_id: str, db: Session = Depends(get_db)):
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )

    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    return render_template(
        request,
        "assignment/grade.html",
        {
            "submission": submission,
        }
    )


# =========================================================
# 1.3) POST chấm bài
# =========================================================
@router.post("/grade/{submission_id}")
def grade_submit(
    request: Request,
    submission_id: str,
    grade: float = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db),
):
    submission = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.id == submission_id)
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    teacher_id = None
    if hasattr(request, "session") and request.session:
        teacher_id = request.session.get("user_id")

    try:
        grade_submission(
            db=db,
            submission_id=submission_id,
            grade=grade,
            feedback=feedback,
            teacher_id=teacher_id,
        )

        message = quote("Chấm bài thành công.")
        return RedirectResponse(
            url=f"/admin/assignment/submissions/{submission.assignment_id}?success={message}",
            status_code=303,
        )
    except HTTPException:
        raise




# =========================================================
# 1.4) Admin tải file bài nộp
# =========================================================
@router.get("/download/{file_id}")
def download_assignment_file(file_id: str, db: Session = Depends(get_db)):
    file_info = db.query(AssignmentFile).filter(AssignmentFile.id == file_id).first()
    if not file_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")

    file_url = str(file_info.file_url or "").strip()
    if _is_remote_url(file_url):
        return RedirectResponse(file_url, status_code=302)

    file_path = _resolve_admin_download_path(file_url)
    if not file_path:
        raise HTTPException(status_code=404, detail="File không tồn tại trên hệ thống.")

    return FileResponse(
        path=str(file_path),
        filename=file_info.file_name or file_path.name,
        media_type=file_info.file_type or "application/octet-stream",
    )


# =========================================================
# 2) Form tạo bài tập
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_assignment_form(request: Request, db: Session = Depends(get_db)):
    teachers = filter_users_by_role(db.query(User), "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).all()

    return render_template(
        request,
        "assignment/create.html",
        {
            "teachers": teachers,
            "courses": courses,
            "modules": modules,
            "form_data": {},
        }
    )


# =========================================================
# 2.1) POST tạo bài tập
# =========================================================
@router.post("/create", response_class=HTMLResponse)
def create_assignment_route(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    course_id: str = Form(...),
    teacher_id: str = Form(""),
    module_id: str = Form(""),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
):
    form_data = {
        "title": title,
        "description": description,
        "course_id": course_id,
        "teacher_id": teacher_id,
        "module_id": module_id,
        "due_date": due_date,
    }

    teachers = filter_users_by_role(db.query(User), "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).all()

    try:
        parsed_due_date = datetime.fromisoformat(due_date) if due_date else None

        create_assignment(
            db,
            title=title,
            description=description,
            course_id=course_id,
            due_date=parsed_due_date,
            teacher_id=teacher_id or None,
            module_id=module_id or None,
        )

        message = quote("Tạo bài tập thành công.")
        return RedirectResponse(url=f"/admin/assignment/list?success={message}", status_code=303)

    except HTTPException as e:
        return render_template(
            request,
            "assignment/create.html",
            {
                "teachers": teachers,
                "courses": courses,
                "modules": modules,
                "form_data": form_data,
                "error": e.detail,
            },
            status_code=e.status_code,
        )


# =========================================================
# 3) Sửa bài tập
# =========================================================
@router.get("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_form(assignment_id: str, request: Request, db: Session = Depends(get_db)):
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    teachers = filter_users_by_role(db.query(User), "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).all()

    return render_template(
        request,
        "assignment/edit.html",
        {
            "assignment": assignment,
            "teachers": teachers,
            "courses": courses,
            "modules": modules,
        }
    )


@router.post("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_route(
    assignment_id: str,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    course_id: str = Form(...),
    teacher_id: str = Form(""),
    module_id: str = Form(""),
    due_date: str = Form(""),
    db: Session = Depends(get_db),
):
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    teachers = filter_users_by_role(db.query(User), "teacher").all()
    courses = db.query(Course).filter(Course.status == "published").all()
    modules = db.query(Module).all()

    try:
        parsed_due_date = datetime.fromisoformat(due_date) if due_date else None

        update_assignment(
            db=db,
            assignment_id=assignment_id,
            title=title,
            description=description,
            course_id=course_id,
            due_date=parsed_due_date,
            teacher_id=teacher_id or None,
            module_id=module_id or None,
        )

        message = quote("Cập nhật bài tập thành công.")
        return RedirectResponse(url=f"/admin/assignment/list?success={message}", status_code=303)

    except HTTPException as e:
        fallback_assignment = assignment
        fallback_assignment.title = title
        fallback_assignment.description = description
        fallback_assignment.course_id = course_id
        fallback_assignment.teacher_id = teacher_id or None
        fallback_assignment.module_id = module_id or None
        fallback_assignment.due_date = parsed_due_date if due_date else None

        return render_template(
            request,
            "assignment/edit.html",
            {
                "assignment": fallback_assignment,
                "teachers": teachers,
                "courses": courses,
                "modules": modules,
                "error": e.detail,
            },
            status_code=e.status_code,
        )


# =========================================================
# 4) Xóa bài tập
# =========================================================
@router.get("/delete/{assignment_id}", response_class=HTMLResponse)
def delete_confirm(assignment_id: str, request: Request, db: Session = Depends(get_db)):
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    return render_template(
        request,
        "assignment/delete.html",
        {
            "assignment": assignment,
        }
    )


@router.post("/delete/{assignment_id}")
def delete_assignment_route(assignment_id: str, db: Session = Depends(get_db)):
    try:
        deleted = delete_assignment(db, assignment_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

        message = quote("Xóa bài tập thành công.")
        return RedirectResponse(f"/admin/assignment/list?success={message}", status_code=303)
    except HTTPException:
        raise


# =========================================================
# 5) Thống kê theo khóa học
# =========================================================
@router.get("/manage/{course_id}", response_class=HTMLResponse)
def manage_assignments(request: Request, course_id: str, db: Session = Depends(get_db)):
    stats = get_assignment_analytics(db, course_id)
    course = db.query(Course).filter(Course.id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy khóa học.")

    return render_template(
        request,
        "assignment/manage.html",
        {
            "stats": stats,
            "course": course,
        }
    )


# =========================================================
# 6) Dashboard thống kê tổng hợp
# =========================================================
@router.get("/stats", response_class=HTMLResponse)
def assignment_stats_dashboard(request: Request, db: Session = Depends(get_db)):
    global_stats = get_global_assignment_report(db)

    teacher_stats = [
        {
            "teacher_name": _display_name(t),
            "data": get_teacher_assignment_stats(db, t.id),
        }
        for t in filter_users_by_role(db.query(User), "teacher").all()
    ]

    student_stats = [
        {
            "student_name": _display_name(s),
            "data": get_student_assignment_summary(db, s.id),
        }
        for s in filter_users_by_role(db.query(User), "student").limit(5).all()
    ]

    return render_template(
        request,
        "assignment/stats.html",
        {
            "global_stats": global_stats,
            "teacher_stats": teacher_stats,
            "student_stats": student_stats,
        }
    )


# =========================================================
# 7) Xuất Excel
# =========================================================
@router.get("/export_excel/{assignment_id}")
def export_assignment_excel(assignment_id: str, db: Session = Depends(get_db)):
    assignment = get_by_id(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)

    file_path = export_dir / f"assignment_{assignment_id}.xlsx"
    export_assignment_scores_to_excel(db, assignment_id, str(file_path))

    return FileResponse(
        str(file_path),
        filename=file_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )