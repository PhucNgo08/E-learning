from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database.connection import get_db
from app.models.quiz import Quiz
from app.models.course import Course   # ✅ thêm import
import uuid
import traceback

# ==============================
# 🧭 Template config
# ==============================
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/admin/exams"
)

# ==============================
# 🚀 Router
# ==============================
exam_router = APIRouter(
    prefix="/admin/exams",
    tags=["Admin - Exam Management"]
)


# =========================================================
# 📋 1️⃣ Danh sách kỳ thi
# =========================================================
@exam_router.get("/manage", response_class=HTMLResponse)
def manage_exams(request: Request, db: Session = Depends(get_db)):
    """Hiển thị danh sách kỳ thi trong hệ thống."""
    try:
        exams = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
        print(f"📘 Có {len(exams)} kỳ thi được tìm thấy.")
        return templates.TemplateResponse(
            "manage.html",
            {"request": request, "exams": exams, "current_year": datetime.now().year},
        )
    except Exception:
        print("\n❌ LỖI HIỂN THỊ DANH SÁCH KỲ THI:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)


# =========================================================
# ➕ 2️⃣ Tạo kỳ thi mới
# =========================================================
@exam_router.get("/create", response_class=HTMLResponse)
def create_exam_form(request: Request, db: Session = Depends(get_db)):
    """Trang hiển thị form tạo kỳ thi."""
    courses = db.query(Course).all()  # ✅ Lấy danh sách khóa học
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "courses": courses},  # ✅ Gửi danh sách xuống template
    )


@exam_router.post("/create", response_class=HTMLResponse)
def create_exam(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    course_id: str = Form(None),
    total_questions: int = Form(10),
    db: Session = Depends(get_db),
):
    """Xử lý tạo kỳ thi mới."""
    try:
        # ✅ Nếu course_id rỗng thì gán None
        if not course_id:
            course_id = None
        else:
            # Kiểm tra khóa học có tồn tại không
            course_exists = db.query(Course).filter(Course.id == course_id).first()
            if not course_exists:
                raise HTTPException(status_code=400, detail="Khóa học không hợp lệ hoặc không tồn tại.")

        new_exam = Quiz(
            id=str(uuid.uuid4()),
            title=title.strip(),
            description=description.strip() if description else None,
            course_id=course_id,  # ✅ Lưu ID thật
            total_questions=total_questions,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(new_exam)
        db.commit()
        db.refresh(new_exam)
        print(f"✅ Tạo kỳ thi mới: {title}")
        return RedirectResponse(url="/admin/exams/manage", status_code=303)
    except Exception:
        db.rollback()
        print("\n❌ LỖI TẠO KỲ THI:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)

# =========================================================
# ✏️ 3️⃣ Chỉnh sửa kỳ thi
# =========================================================
@exam_router.get("/edit/{exam_id}", response_class=HTMLResponse)
def edit_exam_form(request: Request, exam_id: str, db: Session = Depends(get_db)):
    """Trang chỉnh sửa thông tin kỳ thi."""
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi.")
    return templates.TemplateResponse("edit.html", {"request": request, "exam": exam})


@exam_router.post("/edit/{exam_id}")
def update_exam(
    exam_id: str,
    title: str = Form(...),
    description: str = Form(None),
    total_questions: int = Form(10),
    db: Session = Depends(get_db),
):
    """Cập nhật kỳ thi."""
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi cần cập nhật.")
    try:
        exam.title = title.strip()
        exam.description = description.strip() if description else None
        exam.total_questions = total_questions
        exam.updated_at = datetime.now()
        db.commit()
        db.refresh(exam)
        print(f"✏️ Đã cập nhật kỳ thi: {exam.title}")
        return RedirectResponse(url="/admin/exams/manage", status_code=303)
    except Exception:
        db.rollback()
        print("\n❌ LỖI CẬP NHẬT KỲ THI:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)


# =========================================================
# 🗑️ 4️⃣ Xóa kỳ thi
# =========================================================
@exam_router.get("/delete/{exam_id}", response_class=HTMLResponse)
def delete_exam_confirm(request: Request, exam_id: str, db: Session = Depends(get_db)):
    """Trang xác nhận xóa kỳ thi."""
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi.")
    return templates.TemplateResponse("delete.html", {"request": request, "exam": exam})


@exam_router.post("/delete/{exam_id}")
def delete_exam(exam_id: str, db: Session = Depends(get_db)):
    """Xóa kỳ thi khỏi hệ thống."""
    exam = db.query(Quiz).filter(Quiz.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy kỳ thi.")
    try:
        db.delete(exam)
        db.commit()
        print(f"🗑️ Đã xóa kỳ thi: {exam.title}")
        return RedirectResponse(url="/admin/exams/manage", status_code=303)
    except Exception:
        db.rollback()
        print("\n❌ LỖI XÓA KỲ THI:\n", traceback.format_exc())
        return HTMLResponse(f"<pre>{traceback.format_exc()}</pre>", status_code=500)
