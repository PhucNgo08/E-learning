from datetime import datetime
from pathlib import Path
import io
import traceback

from fastapi import APIRouter, Request, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
from app.models.assignment_file import AssignmentFile
from app.models.user import User
from app.models.course import Course
from app.models.module import Module

from app.database.connection import get_db
from app.services.teacher import assignment_service
from app.dependencies.auth import get_current_teacher
from app.config.template_config import get_template_by_path

router = APIRouter(
    prefix="/teacher/assignments",
    tags=["Teacher - Assignments"]
)

BACKEND_DIR = Path(__file__).resolve().parents[3]


async def read_assignment_text_file(file: UploadFile | None) -> str:
    """
    Đọc file văn bản đề bài tập (.txt/.md) và trả về nội dung.
    Nội dung này được lưu vào assignments.description theo đúng schema e_learning.
    """
    if not file or not getattr(file, "filename", None):
        return ""

    filename = str(file.filename).strip()
    if not filename:
        return ""

    name = filename.lower()
    if not name.endswith((".txt", ".md")):
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ file văn bản .txt hoặc .md để đọc đề bài tập.",
        )

    content = await file.read()
    if not content:
        return ""

    return content.decode("utf-8-sig", errors="ignore").strip()


def _is_remote_url(value: str) -> bool:
    lower = (value or "").lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _resolve_teacher_download_path(file_url: str) -> Path | None:
    """
    Hỗ trợ cả 2 kiểu đang có trong project:
    - Đường dẫn tuyệt đối được lưu từ service nộp bài
    - URL static /uploads/... được mount từ backend/app/uploads
    """
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


@router.get("/", include_in_schema=False)
def redirect_root_to_list():
    return RedirectResponse("/teacher/assignments/list", status_code=303)


@router.get("/list", response_class=HTMLResponse)
def list_assignments(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        assignments = assignment_service.get_assignments_by_teacher(db, current_teacher.id)
        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "assignments/list.html",
            {
                "request": request,
                "assignments": assignments,
                "now": datetime.now(),
                "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
            },
        )
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tải danh sách bài tập")


@router.get("/create", response_class=HTMLResponse)
def create_form(
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        teacher_id = current_teacher.id
        courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()

        course_ids = [c.id for c in courses]
        modules = (
            db.query(Module)
            .filter(Module.course_id.in_(course_ids))
            .order_by(Module.course_id, Module.module_number)
            .all()
            if course_ids else []
        )

        templates = get_template_by_path(str(request.url.path))
        return templates.TemplateResponse(
            "assignments/create.html",
            {
                "request": request,
                "courses": courses,
                "modules": modules,
                "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
            },
        )
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tải form tạo bài tập")


@router.post("/create")
async def create_assignment(
    course_id: str = Form(...),
    module_id: str = Form(None),
    title: str = Form(...),
    description: str = Form(""),
    due_date: str = Form(...),
    assignment_text_file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        file_description = await read_assignment_text_file(assignment_text_file)

        final_description = (description or "").strip()
        if file_description:
            final_description = (
                f"{final_description}\n\n{file_description}"
                if final_description
                else file_description
            )

        assignment_service.create_assignment(
            db=db,
            course_id=course_id,
            module_id=module_id or None,
            teacher_id=current_teacher.id,
            title=title,
            description=final_description,
            due_date=datetime.fromisoformat(due_date),
        )
        return RedirectResponse("/teacher/assignments/list", status_code=303)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể tạo bài tập")


@router.get("/edit/{assignment_id}", response_class=HTMLResponse)
def edit_assignment_form(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    assignment = assignment_service.get_assignment_owned(db, assignment_id, current_teacher.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/edit.html",
        {
            "request": request,
            "assignment": assignment,
            "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
        },
    )


@router.post("/edit/{assignment_id}")
def update_assignment(
    assignment_id: str,
    title: str = Form(...),
    description: str = Form(""),
    due_date: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        updated = assignment_service.update_assignment_by_teacher(
            db=db,
            assignment_id=assignment_id,
            teacher_id=current_teacher.id,
            title=title,
            description=description,
            due_date=datetime.fromisoformat(due_date),
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")

        return RedirectResponse("/teacher/assignments/list", status_code=303)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể cập nhật bài tập")


@router.post("/delete/{assignment_id}")
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        deleted = assignment_service.delete_assignment_by_teacher(
            db=db,
            assignment_id=assignment_id,
            teacher_id=current_teacher.id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")

        return RedirectResponse("/teacher/assignments/list", status_code=303)

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể xóa bài tập")


@router.get("/submissions/{assignment_id}", response_class=HTMLResponse)
def view_submissions(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    assignment = assignment_service.get_assignment_owned(db, assignment_id, current_teacher.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")

    submissions = assignment_service.get_submissions_by_assignment(db, assignment_id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/submissions.html",
        {
            "request": request,
            "submissions": submissions,
            "assignment": assignment,
            "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
        },
    )


@router.get("/grade/{submission_id}", response_class=HTMLResponse)
def grade_form(
    submission_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    submission = db.query(AssignmentSubmission).filter_by(id=submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")

    assignment = db.query(Assignment).filter_by(id=submission.assignment_id).first()
    if not assignment or assignment.teacher_id != current_teacher.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chấm bài này")

    student = db.query(User).filter(User.id == submission.student_id).first()
    submission.files = assignment_service.get_submission_files(db, submission.id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/grade.html",
        {
            "request": request,
            "submission": submission,
            "student": student,
            "assignment": assignment,
        },
    )


@router.post("/grade/{submission_id}")
def submit_grade(
    submission_id: str,
    grade: float = Form(...),
    feedback: str = Form(""),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        updated = assignment_service.grade_submission(
            db=db,
            submission_id=submission_id,
            grade=grade,
            feedback=feedback,
            teacher_id=current_teacher.id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp")

        return RedirectResponse(
            f"/teacher/assignments/submissions/{updated.assignment_id}",
            status_code=303,
        )

    except HTTPException:
        raise
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Không thể chấm điểm bài nộp")


@router.get("/download/{file_id}")
def download_assignment_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    file_info = (
        db.query(AssignmentFile)
        .join(AssignmentSubmission, AssignmentSubmission.id == AssignmentFile.submission_id)
        .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
        .filter(
            AssignmentFile.id == file_id,
            Assignment.teacher_id == current_teacher.id,
        )
        .first()
    )

    if not file_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy file hoặc bạn không có quyền tải.")

    file_url = str(file_info.file_url or "").strip()
    if _is_remote_url(file_url):
        return RedirectResponse(file_url, status_code=302)

    file_path = _resolve_teacher_download_path(file_url)
    if not file_path:
        raise HTTPException(status_code=404, detail="File không tồn tại trên hệ thống.")

    return FileResponse(
        path=str(file_path),
        filename=file_info.file_name or file_path.name,
        media_type=file_info.file_type or "application/octet-stream",
    )


@router.get("/export/{assignment_id}")
def export_assignment_excel(
    assignment_id: str,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    assignment = assignment_service.get_assignment_owned(db, assignment_id, current_teacher.id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập")

    rows = assignment_service.get_submission_export_rows(db, assignment_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Submissions"

    headers = [
        "STT", "MSSV", "Họ tên", "Email",
        "Thời gian nộp", "Trạng thái", "Điểm",
        "Nhận xét", "Số file", "Nộp trễ?"
    ]
    ws.append(headers)

    header_font = Font(bold=True)
    center = Alignment(horizontal="center")
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.alignment = center
        ws.column_dimensions[cell.column_letter].width = 20

    for idx, r in enumerate(rows, start=1):
        ws.append([
            idx,
            r["mssv"] or "",
            r["full_name"] or "",
            r["email"] or "",
            r["submission_time"].strftime("%Y-%m-%d %H:%M:%S") if r["submission_time"] else "",
            r["status"] or "",
            r["grade"] if r["grade"] is not None else "",
            r["feedback"] or "",
            r["file_count"],
            "Có" if r["is_late"] else "Không",
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"submissions_{assignment.title.replace(' ', '_')}.xlsx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/progress/{course_id}", response_class=HTMLResponse)
def view_course_progress(
    course_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.teacher_id == current_teacher.id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem khóa học này")

    progress_data = assignment_service.get_student_progress_by_course(db, course_id)

    templates = get_template_by_path(str(request.url.path))
    return templates.TemplateResponse(
        "assignments/progress.html",
        {
            "request": request,
            "course": course,
            "progress_data": progress_data,
            "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
        },
    )