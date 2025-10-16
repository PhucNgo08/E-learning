from fastapi import (
    APIRouter,
    Request,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    File
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# ============================
# 📦 Import nội bộ
# ============================
from app.database.connection import get_db
from app.dependencies import get_current_user_id
from app.models.course import Course
from app.models.module import Module
from app.models.lesson import Lesson

# ============================
# 🧭 Cấu hình Template
# ============================
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(
    directory="D:/KhoaHoctructuyen/KHoaHocOnline/frontend/react-app/layouts/templates/teacher/lessons"
)

# ============================
# 🚀 Khởi tạo Router
# ============================
router = APIRouter(
    prefix="/teacher/lessons",
    tags=["Teacher - Lessons Management"]
)

# =========================================================
# 📋 1️⃣ Danh sách bài học theo module
# =========================================================
@router.get("/list/{module_id}", response_class=HTMLResponse)
def list_lessons(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Danh sách bài học trong một module."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem module này.")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_number.asc())
        .all()
    )

    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "lessons": lessons,
            "module": module,
            "course": course,
            "now": datetime.now()
        },
    )

# =========================================================
# 📚 2️⃣ Danh sách tất cả bài học của giáo viên
# =========================================================
@router.get("/list-all", response_class=HTMLResponse)
def list_all_lessons(
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Hiển thị toàn bộ bài học thuộc các khóa học của giáo viên."""
    lessons = (
        db.query(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc(), Module.module_number.asc(), Lesson.lesson_number.asc())
        .all()
    )

    return templates.TemplateResponse(
        "list_all.html",
        {
            "request": request,
            "lessons": lessons,
            "now": datetime.now()
        },
    )

# =========================================================
# ➕ 3️⃣ Trang tạo bài học (tùy chọn module)
# =========================================================
@router.get("/create", response_class=HTMLResponse)
def create_lesson_general(
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Trang tạo bài học chung (chưa chọn module)."""
    modules = (
        db.query(Module)
        .join(Course, Module.course_id == Course.id)
        .filter(Course.teacher_id == teacher_id)
        .order_by(Course.course_name.asc(), Module.module_number.asc())
        .all()
    )

    return templates.TemplateResponse(
        "create_general.html",
        {"request": request, "modules": modules, "now": datetime.now()}
    )

# =========================================================
# ➕ 4️⃣ Tạo bài học theo module
# =========================================================
@router.get("/create/{module_id}", response_class=HTMLResponse)
def create_lesson_page(
    module_id: str,
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Trang form tạo bài học mới."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo bài học trong module này.")

    return templates.TemplateResponse(
        "create.html",
        {
            "request": request,
            "module": module,
            "course": course,
            "now": datetime.now()
        }
    )


@router.post("/create/{module_id}")
async def create_lesson(
    module_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id),
    title: str = Form(...),
    description: str = Form(""),
    video_url: str = Form(""),
    document_url: str = Form(""),
    thumbnail: UploadFile | None = File(None)
):
    """Xử lý thêm bài học mới (tự động đánh số)."""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Không tìm thấy module.")

    # Xác minh quyền
    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền tạo bài học trong module này.")

    # 🔹 Tự động xác định số thứ tự bài học tiếp theo
    next_number = db.query(Lesson).filter(Lesson.module_id == module_id).count() + 1

    # 🔹 Lưu thumbnail nếu có
    thumbnail_path = None
    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "teacher" / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}_{thumbnail.filename}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(await thumbnail.read())
        thumbnail_path = f"/teacher/uploads/lessons/{filename}"

    # 🔹 Tạo mới bài học
    lesson = Lesson(
        id=str(uuid4()),
        module_id=module_id,
        lesson_number=next_number,
        title=title.strip(),
        description=description.strip(),
        video_url=video_url.strip() if video_url else None,
        document_url=document_url.strip() if document_url else None,
        thumbnail_url=thumbnail_path,
        created_at=datetime.now()
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)

    return RedirectResponse(url=f"/teacher/lessons/list/{module_id}", status_code=303)

# =========================================================
# ✏️ 5️⃣ Sửa bài học
# =========================================================
@router.get("/edit/{lesson_id}", response_class=HTMLResponse)
def edit_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Hiển thị form chỉnh sửa bài học."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bài học này.")

    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "lesson": lesson,
            "module": module,
            "course": course,
            "now": datetime.now()
        }
    )


@router.post("/edit/{lesson_id}")
async def edit_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id),
    title: str = Form(...),
    description: str = Form(""),
    video_url: str = Form(""),
    document_url: str = Form(""),
    thumbnail: UploadFile | None = File(None)
):
    """Xử lý cập nhật bài học."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa bài học này.")

    # Cập nhật dữ liệu
    lesson.title = title.strip()
    lesson.description = description.strip()
    lesson.video_url = video_url.strip() if video_url else None
    lesson.document_url = document_url.strip() if document_url else None

    if thumbnail and thumbnail.filename:
        upload_dir = BASE_DIR / "teacher" / "uploads" / "lessons"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4()}_{thumbnail.filename}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as f:
            f.write(await thumbnail.read())
        lesson.thumbnail_url = f"/teacher/uploads/lessons/{filename}"

    db.commit()
    db.refresh(lesson)

    return RedirectResponse(url=f"/teacher/lessons/list/{lesson.module_id}", status_code=303)

# =========================================================
# ❌ 6️⃣ Xóa bài học
# =========================================================
@router.get("/delete/{lesson_id}", response_class=HTMLResponse)
def delete_lesson_page(
    lesson_id: str,
    request: Request,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Trang xác nhận xóa bài học."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài học này.")

    return templates.TemplateResponse(
        "delete.html",
        {"request": request, "lesson": lesson, "module": module, "course": course, "now": datetime.now()}
    )


@router.post("/delete/{lesson_id}")
def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    teacher_id: str = Depends(get_current_user_id)
):
    """Xử lý xóa bài học."""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài học.")

    module = db.query(Module).filter(Module.id == lesson.module_id).first()
    course = db.query(Course).filter(Course.id == module.course_id, Course.teacher_id == teacher_id).first()
    if not course:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài học này.")

    module_id = lesson.module_id
    db.delete(lesson)
    db.commit()

    return RedirectResponse(url=f"/teacher/lessons/list/{module_id}", status_code=303)
