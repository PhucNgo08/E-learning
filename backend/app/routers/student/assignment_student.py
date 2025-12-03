"""
==========================================================
🎓 ROUTER: Student - Assignment (FINAL PRO MAX 2025)
Xử lý đầy đủ chức năng bài tập học viên CHUẨN HỆ THỐNG
==========================================================
"""

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,
    File,
    HTTPException
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette import status
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path

from app.database.connection import get_db
from app.services.student import assignment_service
from app.config.template_config import templates

from app.models.enrollment import Enrollment
from app.models.assignment import Assignment

router = APIRouter(
    prefix="/student/assignment",
    tags=["Student - Assignment"]
)


# ==========================================================
# 1. Trang danh sách bài đã nộp
# ==========================================================
@router.get("/", response_class=HTMLResponse)
async def assignment_home(request: Request, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    submissions = assignment_service.get_my_submissions(db, student_id) or []

    return templates["student"].TemplateResponse(
        "assignment/my_submissions.html",
        {
            "request": request,
            "submissions": submissions,
            "page_title": "📘 Bài tập đã nộp",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 2. Danh sách bài tập theo khóa học
# ==========================================================
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_assignments(request: Request, course_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    assignments = assignment_service.get_assignments_by_course(db, course_id) or []

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "course_id": course_id,
            "now": datetime.utcnow(),
            "page_title": "📚 Danh sách bài tập",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 3. Xem chi tiết bài tập
# ==========================================================
@router.get("/detail/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    assignment = assignment_service.get_assignment_detail(db, assignment_id)

    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    return templates["student"].TemplateResponse(
        "assignment/detail.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": f"📄 {assignment.title}",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 4. Trang form nộp bài
# ==========================================================
@router.get("/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_page(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    assignment = assignment_service.get_assignment_detail(db, assignment_id)

    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

    return templates["student"].TemplateResponse(
        "assignment/submit.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": "📤 Nộp bài tập",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 5. Submit nộp bài (POST)
# ==========================================================
@router.post("/submit/{assignment_id}")
async def submit_assignment(
    request: Request,
    assignment_id: str,
    submission_text: str = Form(""),
    files: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    result = assignment_service.submit_assignment(
        db=db,
        assignment_id=assignment_id,
        student_id=student_id,
        submission_text=submission_text,
        files=files
    )

    if result.get("status") == "error":
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": f"❌ {result['message']}"},
            status_code=400
        )

    return RedirectResponse(
        url=f"/student/assignment/result/{assignment_id}",
        status_code=status.HTTP_303_SEE_OTHER
    )


# ==========================================================
# 6. Xem kết quả nộp bài
# ==========================================================
@router.get("/result/{assignment_id}", response_class=HTMLResponse)
async def view_result(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    submissions = assignment_service.get_my_submissions(db, student_id) or []
    my_submissions = [s for s in submissions if s.assignment_id == assignment_id]

    return templates["student"].TemplateResponse(
        "assignment/result.html",
        {
            "request": request,
            "submissions": my_submissions,
            "page_title": "📊 Kết quả bài nộp",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 7. Chi tiết bài nộp
# ==========================================================
@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_id: str, db: Session = Depends(get_db)):

    submission = assignment_service.get_submission_detail(db, submission_id)

    if not submission:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

    return templates["student"].TemplateResponse(
        "assignment/submission_detail.html",
        {
            "request": request,
            "submission": submission,
            "page_title": "📎 Chi tiết bài nộp",
            "active_page": "assignment"
        }
    )


# ==========================================================
# 8. Download file bài nộp
# ==========================================================
@router.get("/download/{file_id}")
async def download_submission_file(request: Request, file_id: str, db: Session = Depends(get_db)):

    file_info = assignment_service.get_submission_file(db, file_id)

    if not file_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy file.")

    file_path = Path(file_info.file_url)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại trên hệ thống.")

    return FileResponse(
        path=file_path,
        filename=file_info.file_name,
        media_type="application/octet-stream"
    )


# ==========================================================
# 9. Danh sách toàn bộ bài tập student được nhận (FULL FIX)
# ==========================================================
@router.get("/list", response_class=HTMLResponse)
async def assignment_list(request: Request, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    enrollments = db.query(Enrollment).filter_by(user_id=student_id).all()
    course_ids = [e.course_id for e in enrollments]

    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id.in_(course_ids))
        .order_by(Assignment.due_date.asc())
        .all()
    )

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "now": datetime.utcnow(),
            "page_title": "📚 Danh sách bài tập",
            "active_page": "assignment"
        }
    )
