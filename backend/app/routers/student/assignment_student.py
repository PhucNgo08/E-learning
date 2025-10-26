"""
==========================================================
🎓 ROUTER: Student - Assignment
Xử lý các chức năng bài tập của học viên
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
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.student import assignment_service
from app.config.template_config import templates  # ✅ Dùng template động

# ==========================================================
# ⚙️ Cấu hình Router
# ==========================================================
router = APIRouter(
    prefix="/student/assignment",
    tags=["Student - Assignment"]
)


# ----------------------------------------------------------
# 🔹 1. Trang chính /student/assignment → danh sách bài tập đã nộp
# ----------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def assignment_home(request: Request, db: Session = Depends(get_db)):
    """
    📋 Trang mặc định hiển thị tất cả bài tập học viên đã nộp
    """
    student_id = request.session.get("user_id", None)
    if not student_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    submissions = assignment_service.get_my_submissions(db, student_id)
    return templates["student"].TemplateResponse(
        "assignment/list.html",   # ✅ bỏ student/
        {
            "request": request,
            "assignments": submissions,
            "page_title": "📘 Bài tập đã nộp",
            "active_page": "assignment"
        },
    )


# ----------------------------------------------------------
# 🔹 2. Danh sách bài tập của 1 khóa học cụ thể
# ----------------------------------------------------------
@router.get("/course/{course_id}", response_class=HTMLResponse)
async def list_assignments(request: Request, course_id: str, db: Session = Depends(get_db)):
    """
    📘 Hiển thị danh sách bài tập thuộc 1 khóa học cụ thể
    """
    assignments = assignment_service.get_assignments_by_course(db, course_id)
    return templates["student"].TemplateResponse(
        "assignment/list.html",
        {
            "request": request,
            "assignments": assignments,
            "page_title": "📚 Danh sách bài tập",
            "active_page": "assignment"
        },
    )


# ----------------------------------------------------------
# 🔹 3. Xem chi tiết 1 bài tập
# ----------------------------------------------------------
@router.get("/detail/{assignment_id}", response_class=HTMLResponse)
async def assignment_detail(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    """
    🔍 Xem chi tiết nội dung bài tập
    """
    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        return HTMLResponse("❌ Không tìm thấy bài tập", status_code=404)

    return templates["student"].TemplateResponse(
        "assignment/detail.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": f"📄 Chi tiết bài tập: {assignment.title}",
            "active_page": "assignment"
        },
    )


# ----------------------------------------------------------
# 🔹 4. Trang nộp bài (GET)
# ----------------------------------------------------------
@router.get("/submit/{assignment_id}", response_class=HTMLResponse)
async def submit_page(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    """
    📤 Hiển thị form nộp bài
    """
    assignment = assignment_service.get_assignment_detail(db, assignment_id)
    if not assignment:
        return HTMLResponse("❌ Không tìm thấy bài tập", status_code=404)

    return templates["student"].TemplateResponse(
        "assignment/submit.html",
        {
            "request": request,
            "assignment": assignment,
            "page_title": "📤 Nộp bài tập",
            "active_page": "assignment"
        },
    )


# ----------------------------------------------------------
# 🔹 5. Nộp bài (POST)
# ----------------------------------------------------------
@router.post("/submit/{assignment_id}")
async def submit_assignment(
    request: Request,
    assignment_id: str,
    submission_text: str = Form(""),
    files: list[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    📤 Sinh viên nộp bài (có thể kèm file)
    """
    student_id = request.session.get("user_id", None)
    if not student_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    result = assignment_service.submit_assignment(
        db,
        assignment_id=assignment_id,
        student_id=student_id,
        submission_text=submission_text,
        files=files
    )

    if result:
        return RedirectResponse(
            url=f"/student/assignment/result/{assignment_id}",
            status_code=303
        )
    else:
        return HTMLResponse("❌ Nộp bài thất bại, vui lòng thử lại.", status_code=400)


# ----------------------------------------------------------
# 🔹 6. Xem kết quả bài nộp
# ----------------------------------------------------------
@router.get("/result/{assignment_id}", response_class=HTMLResponse)
async def view_result(request: Request, assignment_id: str, db: Session = Depends(get_db)):
    """
    📊 Hiển thị danh sách các lần nộp bài + điểm
    """
    student_id = request.session.get("user_id", None)
    if not student_id:
        return RedirectResponse(url="/auth/login", status_code=303)

    submissions = assignment_service.get_my_submissions(db, student_id)
    target = [s for s in submissions if s.assignment_id == assignment_id]

    return templates["student"].TemplateResponse(
        "assignment/result.html",
        {
            "request": request,
            "submissions": target,
            "page_title": "📊 Kết quả bài nộp",
            "active_page": "assignment"
        },
    )


# ----------------------------------------------------------
# 🔹 7. Chi tiết một lần nộp bài (file & điểm)
# ----------------------------------------------------------
@router.get("/submission/{submission_id}", response_class=HTMLResponse)
async def submission_detail(request: Request, submission_id: str, db: Session = Depends(get_db)):
    """
    🔎 Xem chi tiết 1 bài nộp (file đính kèm + phản hồi)
    """
    submission = assignment_service.get_submission_detail(db, submission_id)
    if not submission:
        return HTMLResponse("❌ Không tìm thấy bài nộp", status_code=404)

    return templates["student"].TemplateResponse(
        "assignment/submission_detail.html",
        {
            "request": request,
            "submission": submission,
            "page_title": "📎 Chi tiết bài nộp",
            "active_page": "assignment"
        },
    )
