from datetime import datetime
import io
import traceback

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.assignment_submission import AssignmentSubmission
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
def create_assignment(
    course_id: str = Form(...),
    module_id: str = Form(None),
    title: str = Form(...),
    description: str = Form(""),
    due_date: str = Form(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
):
    try:
        assignment_service.create_assignment(
            db=db,
            course_id=course_id,
            module_id=module_id or None,
            teacher_id=current_teacher.id,
            title=title,
            description=description,
            due_date=datetime.fromisoformat(due_date),
        )
        return RedirectResponse("/teacher/assignments/list", status_code=303)

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