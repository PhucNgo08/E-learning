from datetime import datetime
from pathlib import Path
import io
import os
import re
import shutil
import traceback
import uuid

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


DEFAULT_ALLOWED_FILE_TYPES = (
    "jpg,jpeg,png,webp,gif,pdf,doc,docx,ppt,pptx,xls,xlsx,"
    "zip,rar,7z,txt,md,py,html,css,js,json,sql,mp4"
)
TEACHER_ATTACHMENT_DIR = BACKEND_DIR / "app" / "uploads" / "assignments" / "teacher_attachments"
MAX_TEACHER_ATTACHMENT_SIZE_MB = 100


def _safe_filename(filename: str) -> str:
    """Tạo tên file an toàn, tránh tiếng Việt/ký tự lạ làm lỗi URL."""
    raw = os.path.basename(str(filename or "file")).strip()
    stem, ext = os.path.splitext(raw)
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "file"
    ext = re.sub(r"[^A-Za-z0-9.]+", "", ext.lower())
    return f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}_{stem}{ext}"


def _get_form_text(form, name: str, default: str = "") -> str:
    value = form.get(name)
    if value is None:
        return default
    return str(value).strip()


def _get_form_int(form, name: str, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    try:
        value = int(form.get(name) or default)
    except Exception:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _get_form_float(form, name: str, default: float, minimum: float = 0, maximum: float | None = None) -> float:
    try:
        value = float(form.get(name) or default)
    except Exception:
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _parse_datetime_local(value: str) -> datetime:
    value = str(value or "").strip()
    if not value:
        raise ValueError("Vui lòng chọn hạn nộp.")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Hạn nộp không đúng định dạng.") from exc


def _get_uploads(form, *field_names: str) -> list:
    """Lấy file từ nhiều tên input để tránh lệch template gây lỗi."""
    uploads = []
    for name in field_names:
        try:
            values = form.getlist(name)
        except Exception:
            values = []
        for item in values:
            filename = getattr(item, "filename", None)
            if filename and str(filename).strip():
                uploads.append(item)
    return uploads


async def _read_text_uploads(files: list) -> str:
    """Đọc nội dung file .txt/.md để ghép vào mô tả bài tập."""
    parts = []
    for file in files or []:
        filename = str(getattr(file, "filename", "") or "")
        if not filename.lower().endswith((".txt", ".md")):
            raise HTTPException(status_code=400, detail="File đề dạng văn bản chỉ hỗ trợ .txt hoặc .md.")
        content = await file.read()
        if content:
            parts.append(content.decode("utf-8-sig", errors="ignore").strip())
    return "\n\n".join([p for p in parts if p])


async def _save_teacher_attachments(files: list) -> list[dict]:
    """
    Lưu file đề bài giáo viên đính kèm mà không đổi database.
    Link file sẽ được ghép vào assignments.description.
    Không cho upload .exe/.bat/.cmd/.msi vì nguy hiểm khi chia sẻ.
    """
    saved = []
    if not files:
        return saved

    TEACHER_ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    blocked_exts = {"exe", "bat", "cmd", "com", "msi", "scr", "ps1", "vbs", "jar"}

    for file in files:
        filename = str(getattr(file, "filename", "") or "").strip()
        if not filename:
            continue

        ext = Path(filename).suffix.lower().lstrip(".")
        if ext in blocked_exts:
            raise HTTPException(status_code=400, detail=f"Không cho phép upload file thực thi: .{ext}")

        safe_name = _safe_filename(filename)
        target = TEACHER_ATTACHMENT_DIR / safe_name

        size = 0
        with target.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_TEACHER_ATTACHMENT_SIZE_MB * 1024 * 1024:
                    try:
                        target.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=400,
                        detail=f"File {filename} vượt quá {MAX_TEACHER_ATTACHMENT_SIZE_MB}MB.",
                    )
                buffer.write(chunk)

        saved.append({
            "name": filename,
            "url": f"/uploads/assignments/teacher_attachments/{safe_name}",
            "size": size,
        })

    return saved


def _append_attachment_links(description: str, attachments: list[dict]) -> str:
    """Ghép danh sách link file vào mô tả, dùng lại cột description nên không đổi DB."""
    description = (description or "").strip()
    if not attachments:
        return description

    lines = ["", "---", "Tệp đề bài đính kèm:"]
    for item in attachments:
        size_mb = (int(item.get("size") or 0) / 1024 / 1024)
        lines.append(f"- {item.get('name')}: {item.get('url')} ({size_mb:.2f} MB)")
    return (description + "\n" + "\n".join(lines)).strip()


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
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    """
    FIX 422 + hỗ trợ giáo viên đính kèm nhiều file đề bài.
    Đọc form thủ công để không bị lỗi FastAPI 422 nếu input file thiếu/lệch tên.
    """
    try:
        form = await request.form()

        course_id = _get_form_text(form, "course_id")
        module_id = _get_form_text(form, "module_id") or None
        title = _get_form_text(form, "title")
        description = _get_form_text(form, "description")
        due_date_raw = _get_form_text(form, "due_date")

        submission_type = _get_form_text(form, "submission_type", "individual") or "individual"
        allowed_file_types = _get_form_text(form, "allowed_file_types", DEFAULT_ALLOWED_FILE_TYPES) or DEFAULT_ALLOWED_FILE_TYPES
        max_files = _get_form_int(form, "max_files", 5, minimum=1, maximum=50)
        max_file_size_mb = _get_form_int(form, "max_file_size_mb", 50, minimum=1, maximum=500)
        allow_late_submission = form.get("allow_late_submission") is not None
        late_penalty_percent = _get_form_float(form, "late_penalty_percent", 0, minimum=0, maximum=100)
        total_points = _get_form_float(form, "total_points", 10, minimum=0, maximum=100)
        grading_criteria = _get_form_text(form, "grading_criteria")

        if not course_id:
            raise HTTPException(status_code=400, detail="Vui lòng chọn khóa học.")
        if not title:
            raise HTTPException(status_code=400, detail="Vui lòng nhập tiêu đề bài tập.")

        due_date = _parse_datetime_local(due_date_raw)

        text_files = _get_uploads(form, "assignment_text_file", "assignment_text_files")
        attachment_files = _get_uploads(
            form,
            "assignment_attachments",
            "assignment_attachment",
            "assignment_files",
            "files",
        )

        text_from_files = await _read_text_uploads(text_files)
        if text_from_files:
            description = (description + "\n\n" + text_from_files) if description else text_from_files

        saved_attachments = await _save_teacher_attachments(attachment_files)
        final_description = _append_attachment_links(description, saved_attachments)

        assignment_service.create_assignment(
            db=db,
            course_id=course_id,
            module_id=module_id,
            teacher_id=current_teacher.id,
            title=title,
            description=final_description,
            due_date=due_date,
            submission_type=submission_type,
            allowed_file_types=allowed_file_types,
            max_files=max_files,
            max_file_size_mb=max_file_size_mb,
            allow_late_submission=allow_late_submission,
            late_penalty_percent=late_penalty_percent,
            total_points=total_points,
            grading_criteria=grading_criteria,
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

    courses = db.query(Course).filter(Course.teacher_id == current_teacher.id).all()
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
        "assignments/edit.html",
        {
            "request": request,
            "assignment": assignment,
            "courses": courses,
            "modules": modules,
            "teacher_name": getattr(current_teacher, "full_name", None) or getattr(current_teacher, "username", ""),
        },
    )


@router.post("/edit/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    """Cập nhật cả cấu hình nộp file và cho phép thêm file đề bài mới."""
    try:
        form = await request.form()

        title = _get_form_text(form, "title")
        description = _get_form_text(form, "description")
        due_date = _parse_datetime_local(_get_form_text(form, "due_date"))

        submission_type = _get_form_text(form, "submission_type", "individual") or "individual"
        allowed_file_types = _get_form_text(form, "allowed_file_types", DEFAULT_ALLOWED_FILE_TYPES) or DEFAULT_ALLOWED_FILE_TYPES
        max_files = _get_form_int(form, "max_files", 5, minimum=1, maximum=50)
        max_file_size_mb = _get_form_int(form, "max_file_size_mb", 50, minimum=1, maximum=500)
        allow_late_submission = form.get("allow_late_submission") is not None
        late_penalty_percent = _get_form_float(form, "late_penalty_percent", 0, minimum=0, maximum=100)
        total_points = _get_form_float(form, "total_points", 10, minimum=0, maximum=100)
        grading_criteria = _get_form_text(form, "grading_criteria")

        attachment_files = _get_uploads(
            form,
            "assignment_attachments",
            "assignment_attachment",
            "assignment_files",
            "files",
        )
        saved_attachments = await _save_teacher_attachments(attachment_files)
        final_description = _append_attachment_links(description, saved_attachments)

        updated = assignment_service.update_assignment_by_teacher(
            db=db,
            assignment_id=assignment_id,
            teacher_id=current_teacher.id,
            title=title,
            description=final_description,
            due_date=due_date,
            submission_type=submission_type,
            allowed_file_types=allowed_file_types,
            max_files=max_files,
            max_file_size_mb=max_file_size_mb,
            allow_late_submission=allow_late_submission,
            late_penalty_percent=late_penalty_percent,
            total_points=total_points,
            grading_criteria=grading_criteria,
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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