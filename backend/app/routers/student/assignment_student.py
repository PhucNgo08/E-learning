"""
==========================================================
🎓 ROUTER: Student - Assignment
Xử lý đầy đủ chức năng bài tập học viên (FULL VERSION)
==========================================================
"""

from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    UploadFile,
    File
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from starlette import status
from sqlalchemy.orm import Session
from pathlib import Path
import traceback

from app.database.connection import get_db
from app.services.student import assignment_service
from app.config.template_config import templates


# ==========================================================
# ⚙️ Cấu hình Router
# ==========================================================
router = APIRouter(
    prefix="/student/assignment",
    tags=["Student - Assignment"]
)


# ----------------------------------------------------------
# 🔹 1. Danh sách bài nộp của tôi
# ----------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def assignment_home(request: Request, db: Session = Depends(get_db)):
    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    submissions = assignment_service.get_my_submissions(db, student_id)

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": submissions,
            "page_title": "📘 Bài tập đã nộp",
            "active_page": "assignment"
        }
    )


# ----------------------------------------------------------
# 🔹 2. Danh sách bài tập theo khóa học
# ----------------------------------------------------------
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_assignments(request: Request, course_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    assignments = assignment_service.get_assignments_by_course(db, course_id)

    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "page_title": "📚 Danh sách bài tập",
            "active_page": "assignment"
        }
    )


# ----------------------------------------------------------
# 🔹 3. Xem chi tiết bài tập
# ----------------------------------------------------------
@router.get("/detail/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        return templates["student"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": "❌ Không tìm thấy bài tập."
            },
            status_code=404
        )

    return templates["student"].TemplateResponse(
        "assignment/detail.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": f"📄 Chi tiết bài tập: {assignment.title}",
            "active_page": "assignment"
        }
    )


# ----------------------------------------------------------
# 🔹 4. Trang nộp bài
# ----------------------------------------------------------
@router.get("/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_page(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Không tìm thấy bài tập."},
            status_code=404
        )

    return templates["student"].TemplateResponse(
        "assignment/submit.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": "📤 Nộp bài tập",
            "active_page": "assignment"
        }
    )


# ----------------------------------------------------------
# 🔹 5. Nộp bài (POST) — FULL CHECK & VALIDATE
# ----------------------------------------------------------
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

    try:
        result = assignment_service.submit_assignment(
            db=db,
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=submission_text,
            files=files
        )

        if not result:
            return templates["student"].TemplateResponse(
                "error.html",
                {"request": request, "message": "❌ Không thể nộp bài. Vui lòng thử lại."},
                status_code=400
            )

        return RedirectResponse(
            url=f"/student/assignment/result/{assignment_id}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        traceback.print_exc()
        return templates["student"].TemplateResponse(
            "error.html",
            {
                "request": request,
                "message": f"⚠️ Lỗi khi nộp bài: {str(e)}"
            },
            status_code=400
        )


# ----------------------------------------------------------
# 🔹 6. Xem kết quả bài nộp
# ----------------------------------------------------------
@router.get("/result/{assignment_id}", response_class=HTMLResponse)
async def view_result(request: Request, assignment_id: str, db: Session = Depends(get_db)):

    student_id = request.session.get("user_id")
    if not student_id:
        return RedirectResponse("/auth/login", status.HTTP_302_FOUND)

    submissions = assignment_service.get_my_submissions(db, student_id)
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


# ----------------------------------------------------------
# 🔹 7. Chi tiết bài nộp (file & điểm)
# ----------------------------------------------------------
@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_id: str, db: Session = Depends(get_db)):

    submission = assignment_service.get_submission_detail(db, submission_id)
    if not submission:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Không tìm thấy bài nộp."},
            status_code=404
        )

    return templates["student"].TemplateResponse(
        "assignment/submission_detail.html",
        {
            "request": request,
            "submission": submission,
            "page_title": "📎 Chi tiết bài nộp",
            "active_page": "assignment"
        }
    )


# ----------------------------------------------------------
# 🔹 8. Tải file bài nộp
# ----------------------------------------------------------
@router.get("/download/{file_id}")
async def download_submission_file(request: Request, file_id: str, db: Session = Depends(get_db)):

    file_info = assignment_service.get_submission_file(db, file_id)
    if not file_info:
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "❌ Không tìm thấy file bài nộp."},
            status_code=404
        )

    file_path = Path(file_info.file_url)
    if not file_path.exists():
        return templates["student"].TemplateResponse(
            "error.html",
            {"request": request, "message": "⚠️ File không tồn tại trên hệ thống."},
            status_code=404
        )

    return FileResponse(
        path=file_path,
        filename=file_info.file_name,
        media_type="application/octet-stream"
    )
