from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette import status
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.config.template_config import templates
from app.database.connection import get_db
from app.models.assignment import Assignment
from app.models.course import Course
from app.services.student import assignment_service


router = APIRouter(
    prefix="/student/assignment",
    tags=["Student - Assignment"],
)


def get_current_student_id(request: Request) -> str | None:
    """
    Lấy student_id từ session.
    Một số file login lưu role là "role", một số bản lưu "user_role"/"current_role".
    Nếu có role thì bắt buộc là student; nếu không có role nhưng có user_id thì vẫn cho qua
    để tránh lỗi không vào được do session cũ thiếu role.
    """
    user_id = request.session.get("user_id")
    role = (
        request.session.get("role")
        or request.session.get("user_role")
        or request.session.get("current_role")
    )

    if not user_id:
        return None

    if role and str(role).lower() != "student":
        return None

    return str(user_id)


def _redirect_login_if_needed(request: Request) -> str | RedirectResponse:
    student_id = get_current_student_id(request)
    if not student_id:
        return RedirectResponse("/auth/login", status_code=status.HTTP_302_FOUND)
    return student_id


def _build_submission_maps(submissions: list) -> tuple[dict, dict]:
    submission_by_assignment: dict[str, object] = {}
    status_by_assignment: dict[str, str] = {}

    for submission in submissions or []:
        assignment_id = str(submission.assignment_id)
        existing = submission_by_assignment.get(assignment_id)

        if not existing:
            submission_by_assignment[assignment_id] = submission
            status_by_assignment[assignment_id] = str(submission.status or "submitted")
            continue

        current_time = getattr(submission, "submission_time", None)
        existing_time = getattr(existing, "submission_time", None)
        if current_time and (not existing_time or current_time > existing_time):
            submission_by_assignment[assignment_id] = submission
            status_by_assignment[assignment_id] = str(submission.status or "submitted")

    return submission_by_assignment, status_by_assignment


def _render_submit_page(
    request: Request,
    assignment,
    current_submission=None,
    *,
    error_message: str | None = None,
    submitted_text: str = "",
    status_code: int = 200,
):
    return templates["student"].TemplateResponse(
        "assignment/submit.html",
        {
            "request": request,
            "assignment": assignment,
            "current_submission": current_submission,
            "error_message": error_message,
            "submitted_text": submitted_text,
            "page_title": "Nộp bài tập",
            "active_page": "assignment",
            "now": datetime.utcnow(),
        },
        status_code=status_code,
    )


def _get_form_text(form, *names: str) -> str:
    for name in names:
        value = form.get(name)
        if value is not None:
            return str(value).strip()
    return ""


def _get_form_files(form, *names: str) -> list:
    """
    Lấy file từ nhiều tên input khác nhau để tránh lỗi 422 hoặc không nhận file.
    Hỗ trợ:
    - name="files"
    - name="file"
    - name="attachments"
    - name="upload_files"
    """
    result = []

    for name in names:
        try:
            values = form.getlist(name)
        except Exception:
            values = []

        for value in values:
            filename = getattr(value, "filename", None)
            if not filename:
                continue
            if not str(filename).strip():
                continue
            result.append(value)

    return result


@router.get("/", response_class=HTMLResponse)
async def assignment_home(request: Request, db: Session = Depends(get_db)):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    submissions = assignment_service.get_my_submissions(db, student_id) or []

    return templates["student"].TemplateResponse(
        "assignment/my_submissions.html",
        {
            "request": request,
            "submissions": submissions,
            "page_title": "Bài tập đã nộp",
            "active_page": "assignment",
        },
    )


@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_assignments_by_course(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    if not assignment_service.is_student_enrolled_in_course(db, student_id, course_id):
        return HTMLResponse("Bạn chưa tham gia khóa học này.", status_code=403)

    assignments = assignment_service.get_assignments_by_course(db, course_id) or []
    my_submissions = assignment_service.get_my_submissions(db, student_id) or []
    submission_by_assignment, status_by_assignment = _build_submission_maps(my_submissions)

    course = db.query(Course).filter(Course.id == course_id).first()
    page_title = f"Bài tập khóa học: {course.course_name}" if course else "Danh sách bài tập"

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "course_id": course_id,
            "course": course,
            "submission_by_assignment": submission_by_assignment,
            "status_by_assignment": status_by_assignment,
            "now": datetime.utcnow(),
            "page_title": page_title,
            "active_page": "assignment",
        },
    )


@router.get("/list", response_class=HTMLResponse)
async def assignment_list(request: Request, db: Session = Depends(get_db)):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    assignments = (
        db.query(Assignment)
        .join(Course, Course.id == Assignment.course_id)
        .order_by(Assignment.due_date.asc(), Assignment.created_at.desc())
        .all()
    )

    assignments = [
        assignment
        for assignment in assignments
        if assignment_service.is_student_enrolled_in_course(db, student_id, assignment.course_id)
    ]

    my_submissions = assignment_service.get_my_submissions(db, student_id) or []
    submission_by_assignment, status_by_assignment = _build_submission_maps(my_submissions)

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "submission_by_assignment": submission_by_assignment,
            "status_by_assignment": status_by_assignment,
            "now": datetime.utcnow(),
            "page_title": "Danh sách bài tập",
            "active_page": "assignment",
        },
    )


@router.get("/detail/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    if not assignment_service.is_student_enrolled_in_course(db, student_id, assignment.course_id):
        return HTMLResponse("Bạn không có quyền xem bài tập này.", status_code=403)

    my_submission = assignment_service.get_my_submission_for_assignment(
        db,
        assignment_id,
        student_id,
    )

    return templates["student"].TemplateResponse(
        "assignment/detail.html",
        {
            "request": request,
            "assignment": assignment,
            "my_submission": my_submission,
            "now": datetime.utcnow(),
            "page_title": assignment.title,
            "active_page": "assignment",
        },
    )


@router.get("/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_page(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    if not assignment_service.is_student_enrolled_in_course(db, student_id, assignment.course_id):
        return HTMLResponse("Bạn không có quyền nộp bài cho bài tập này.", status_code=403)

    current_submission = assignment_service.get_my_submission_for_assignment(
        db,
        assignment_id,
        student_id,
    )

    # Lấy lỗi đã lưu trong session nếu có.
    error_message = request.session.get("assignment_error")
    submitted_text = request.session.get("assignment_submitted_text") or ""
    request.session["assignment_error"] = None
    request.session["assignment_submitted_text"] = None

    return _render_submit_page(
        request,
        assignment,
        current_submission,
        error_message=error_message,
        submitted_text=submitted_text,
    )


@router.post("/submit/{assignment_id}")
async def submit_assignment(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
):
    """
    FIX 422:
    Không khai báo submission_text: Form(...) hoặc files: File(...)
    vì FastAPI sẽ chặn request trước khi vào hàm nếu form thiếu field.
    Đọc request.form() thủ công để:
    - Không lỗi 422 khi không chọn file
    - Nhận được nhiều tên input khác nhau
    - Tự trả lỗi đẹp trong trang nộp bài
    """
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    if not assignment_service.is_student_enrolled_in_course(db, student_id, assignment.course_id):
        return HTMLResponse("Bạn không có quyền nộp bài cho bài tập này.", status_code=403)

    form = await request.form()

    submission_text = _get_form_text(
        form,
        "submission_text",
        "answer_text",
        "content",
        "description",
        "text",
    )

    files = _get_form_files(
        form,
        "files",
        "file",
        "attachments",
        "upload_files",
    )

    current_submission = assignment_service.get_my_submission_for_assignment(
        db,
        assignment_id,
        student_id,
    )

    result = assignment_service.submit_assignment(
        db=db,
        assignment_id=assignment_id,
        student_id=student_id,
        submission_text=submission_text,
        files=files,
    )

    if result.get("status") == "error":
        return _render_submit_page(
            request,
            assignment,
            current_submission,
            error_message=result.get("message", "Nộp bài thất bại."),
            submitted_text=submission_text,
            status_code=400,
        )

    submission = result.get("submission")
    if submission and getattr(submission, "id", None):
        return RedirectResponse(
            url=f"/student/assignment/submission/{submission.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url=f"/student/assignment/result/{assignment_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/result/{assignment_id}", response_class=HTMLResponse)
async def view_result(
    request: Request,
    assignment_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    if not assignment_service.is_student_enrolled_in_course(db, student_id, assignment.course_id):
        return HTMLResponse("Bạn không có quyền xem kết quả bài nộp này.", status_code=403)

    my_submission = assignment_service.get_my_submission_for_assignment(
        db,
        assignment_id,
        student_id,
    )
    submissions = [my_submission] if my_submission else []

    return templates["student"].TemplateResponse(
        "assignment/result.html",
        {
            "request": request,
            "assignment": assignment,
            "submissions": submissions,
            "page_title": "Kết quả bài nộp",
            "active_page": "assignment",
        },
    )


@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_detail(
    request: Request,
    submission_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    submission = assignment_service.get_submission_detail(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    if not assignment_service.can_student_access_submission(db, submission, student_id):
        return HTMLResponse("Bạn không có quyền xem bài nộp này.", status_code=403)

    return templates["student"].TemplateResponse(
        "assignment/submission_detail.html",
        {
            "request": request,
            "submission": submission,
            "page_title": "Chi tiết bài nộp",
            "active_page": "assignment",
        },
    )


@router.get("/download/{file_id}")
async def download_submission_file(
    request: Request,
    file_id: str,
    db: Session = Depends(get_db),
):
    student_id = _redirect_login_if_needed(request)
    if isinstance(student_id, RedirectResponse):
        return student_id

    file_info = assignment_service.get_submission_file(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")

    submission = assignment_service.get_submission_detail(db, file_info.submission_id)
    if not assignment_service.can_student_access_submission(db, submission, student_id):
        return HTMLResponse("Bạn không có quyền tải file này.", status_code=403)

    target = assignment_service.resolve_file_response_target(file_info)
    if not target.get("ok"):
        raise HTTPException(
            status_code=404,
            detail=target.get("message", "Không thể tải file."),
        )

    if target.get("type") == "remote":
        return RedirectResponse(
            url=target["url"],
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    return FileResponse(
        path=target["path"],
        filename=file_info.file_name,
        media_type="application/octet-stream",
    )
